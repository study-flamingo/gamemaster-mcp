"""
Tests for the summarize_session tool.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from gamemaster_mcp.main import (
    _summarize_session_impl,
    _create_overlapping_chunks,
    _generate_summary_prompt,
    _generate_chunked_summary_prompt
)


class TestChunking:
    """Tests for text chunking functionality."""

    def test_create_overlapping_chunks_small_text(self):
        """Test chunking with text smaller than chunk size."""
        text = "This is a small text that doesn't need chunking."
        chunks = _create_overlapping_chunks(text, chunk_size=1000, overlap_size=100)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_create_overlapping_chunks_exact_size(self):
        """Test chunking with text exactly at chunk size."""
        text = "a" * 1000
        chunks = _create_overlapping_chunks(text, chunk_size=1000, overlap_size=100)

        assert len(chunks) == 1
        assert len(chunks[0]) == 1000

    def test_create_overlapping_chunks_large_text(self):
        """Test chunking with text larger than chunk size."""
        # Create text with paragraph breaks
        paragraphs = [f"Paragraph {i}.\n\n" for i in range(100)]
        text = "".join(paragraphs)

        chunks = _create_overlapping_chunks(text, chunk_size=500, overlap_size=50)

        # Should create multiple chunks
        assert len(chunks) > 1

        # Each chunk (except possibly last) should be close to chunk_size
        for chunk in chunks[:-1]:
            assert len(chunk) >= 400  # Allow some variance for natural breaks
            assert len(chunk) <= 600

    def test_create_overlapping_chunks_overlap(self):
        """Test that chunks have proper overlap."""
        text = "a" * 300 + "b" * 300 + "c" * 300
        chunks = _create_overlapping_chunks(text, chunk_size=400, overlap_size=100)

        # Should have at least 2 chunks
        assert len(chunks) >= 2

        # Check overlap exists between consecutive chunks
        if len(chunks) >= 2:
            # The end of first chunk should appear in second chunk
            overlap_candidate = chunks[0][-50:]  # Get last 50 chars of first chunk
            assert overlap_candidate in chunks[1]

    def test_create_overlapping_chunks_natural_breaks(self):
        """Test that chunks prefer natural break points."""
        text = "Sentence one. " * 50 + "\n\n" + "Sentence two. " * 50
        chunks = _create_overlapping_chunks(text, chunk_size=500, overlap_size=50)

        # First chunk should end near the paragraph break
        assert chunks[0].endswith("\n\n") or ". " in chunks[0][-20:]


class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_generate_summary_prompt_structure(self):
        """Test that summary prompt has required sections."""
        transcription = "Test transcription text"
        context = "character: Gandalf\nlevel: 20"
        prompt = _generate_summary_prompt(
            transcription=transcription,
            context=context,
            session_number=1,
            detail_level="medium",
            source_type="raw text"
        )

        # Check for key sections
        assert "**Session Number:** 1" in prompt
        assert "**Detail Level:** medium" in prompt
        assert "Campaign Context" in prompt
        assert context in prompt
        assert transcription in prompt
        assert "SessionNote" in prompt

    def test_generate_summary_prompt_detail_levels(self):
        """Test that different detail levels produce different instructions."""
        transcription = "Test"
        context = "test"

        brief_prompt = _generate_summary_prompt(transcription, context, 1, "brief", "test")
        medium_prompt = _generate_summary_prompt(transcription, context, 1, "medium", "test")
        detailed_prompt = _generate_summary_prompt(transcription, context, 1, "detailed", "test")

        # Each should have different instructions
        assert brief_prompt != medium_prompt
        assert medium_prompt != detailed_prompt
        assert brief_prompt != detailed_prompt

        # Check for detail-specific keywords
        assert "concise" in brief_prompt.lower()
        assert "balanced" in medium_prompt.lower()
        assert "comprehensive" in detailed_prompt.lower()

    def test_generate_chunked_summary_prompt_structure(self):
        """Test that chunked prompt has required sections."""
        chunks = ["Chunk 1 text", "Chunk 2 text", "Chunk 3 text"]
        context = "character: Gandalf"
        prompt = _generate_chunked_summary_prompt(
            chunks=chunks,
            context=context,
            session_number=2,
            detail_level="detailed",
            source_type="file: session2.txt"
        )

        # Check for key sections
        assert "**Session Number:** 2" in prompt
        assert "**Chunks:** 3" in prompt
        assert "Campaign Context" in prompt
        assert "Phase 1" in prompt
        assert "Phase 2" in prompt
        assert "Phase 3" in prompt
        assert "deduplicate" in prompt.lower()

        # Check all chunks are included
        for i, chunk in enumerate(chunks):
            assert chunk in prompt
            assert f"Chunk {i+1} of {len(chunks)}" in prompt


@pytest.fixture
def mock_storage():
    """Create a mock storage object with sample data."""
    storage = Mock()

    # Mock characters
    char1 = Mock()
    char1.name = "Gandalf"
    char1.character_class = Mock(name="Wizard", level=20)

    char2 = Mock()
    char2.name = "Aragorn"
    char2.character_class = Mock(name="Ranger", level=18)

    storage.list_characters_detailed.return_value = [char1, char2]

    # Mock NPCs
    npc1 = Mock()
    npc1.name = "Frodo"
    npc1.location = "Rivendell"
    npc1.attitude = "friendly"

    storage.list_npcs_detailed.return_value = [npc1]

    # Mock locations
    loc1 = Mock()
    loc1.name = "Rivendell"
    loc1.location_type = "city"

    storage.list_locations_detailed.return_value = [loc1]

    # Mock quests
    quest1 = Mock()
    quest1.title = "Destroy the Ring"
    quest1.status = "active"
    quest1.objectives = ["Get to Mordor", "Throw ring into Mount Doom"]

    storage.list_quests.return_value = ["Destroy the Ring"]
    storage.get_quest.return_value = quest1

    return storage


class TestSummarizeSessionTool:
    """Tests for the summarize_session tool."""

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_raw_text(self, mock_storage_patch):
        """Test summarize_session with raw transcription text."""
        # Setup mocks
        mock_storage_patch.list_characters_detailed.return_value = []
        mock_storage_patch.list_npcs_detailed.return_value = []
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        transcription = "The party enters the dungeon. Gandalf casts a spell."

        result = _summarize_session_impl(
            transcription=transcription,
            session_number=1,
            detail_level="medium"
        )

        # Should return a prompt (string)
        assert isinstance(result, str)
        assert "**Session Number:** 1" in result
        assert transcription in result
        assert "SessionNote" in result

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_with_speaker_map(self, mock_storage_patch):
        """Test summarize_session with speaker mapping."""
        # Setup mocks
        mock_storage_patch.list_characters_detailed.return_value = []
        mock_storage_patch.list_npcs_detailed.return_value = []
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        transcription = "Speaker 1: I cast fireball. Speaker 2: I dodge."
        speaker_map = {"Speaker 1": "Gandalf", "Speaker 2": "Aragorn"}

        result = _summarize_session_impl(
            transcription=transcription,
            session_number=1,
            speaker_map=speaker_map
        )

        # Speaker labels should be replaced
        assert "Gandalf" in result
        assert "Aragorn" in result
        assert "Speaker 1" not in result or "Speaker 2" not in result  # At least one should be replaced

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_file_input(self, mock_storage_patch, tmp_path):
        """Test summarize_session with file path input."""
        # Setup mocks
        mock_storage_patch.list_characters_detailed.return_value = []
        mock_storage_patch.list_npcs_detailed.return_value = []
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        # Create a temporary transcription file
        transcription_file = tmp_path / "session1.txt"
        transcription_content = "The party fights orcs in the cave."
        transcription_file.write_text(transcription_content, encoding='utf-8')

        result = _summarize_session_impl(
            transcription=str(transcription_file),
            session_number=1
        )

        # Should load and process file content
        assert transcription_content in result
        assert "file: session1.txt" in result

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_large_transcription(self, mock_storage_patch):
        """Test summarize_session with large transcription (chunking)."""
        # Setup mocks
        mock_storage_patch.list_characters_detailed.return_value = []
        mock_storage_patch.list_npcs_detailed.return_value = []
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        # Create a large transcription (>200k chars)
        large_transcription = "The party explores. " * 15000  # ~300k chars

        result = _summarize_session_impl(
            transcription=large_transcription,
            session_number=5
        )

        # Should use chunking strategy
        assert "Chunked" in result
        assert "Phase 1" in result
        assert "Phase 2" in result
        assert "deduplicate" in result.lower()

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_loads_campaign_context(self, mock_storage_patch):
        """Test that summarize_session loads campaign context."""
        # Setup detailed mock with JSON-serializable values
        char = Mock()
        char.name = "Gandalf"
        char.character_class = Mock()
        char.character_class.name = "Wizard"  # Must be a string, not Mock
        char.character_class.level = 20  # Must be an int, not Mock

        npc = Mock()
        npc.name = "Saruman"
        npc.location = "Isengard"
        npc.attitude = "hostile"

        mock_storage_patch.list_characters_detailed.return_value = [char]
        mock_storage_patch.list_npcs_detailed.return_value = [npc]
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        transcription = "Test session"
        _summarize_session_impl(transcription, session_number=1)

        # Verify storage methods were called
        mock_storage_patch.list_characters_detailed.assert_called_once()
        mock_storage_patch.list_npcs_detailed.assert_called_once()
        mock_storage_patch.list_locations_detailed.assert_called_once()
        mock_storage_patch.list_quests.assert_called_once()

    @patch('gamemaster_mcp.main.storage')
    def test_summarize_session_detail_levels(self, mock_storage_patch):
        """Test that different detail levels produce different prompts."""
        # Setup mocks
        mock_storage_patch.list_characters_detailed.return_value = []
        mock_storage_patch.list_npcs_detailed.return_value = []
        mock_storage_patch.list_locations_detailed.return_value = []
        mock_storage_patch.list_quests.return_value = []

        transcription = "Test session"

        brief = _summarize_session_impl(transcription, session_number=1, detail_level="brief")
        medium = _summarize_session_impl(transcription, session_number=1, detail_level="medium")
        detailed = _summarize_session_impl(transcription, session_number=1, detail_level="detailed")

        # Each should produce different prompts
        assert brief != medium
        assert medium != detailed
        assert brief != detailed

        # Check for detail-specific keywords
        assert "concise" in brief.lower()
        assert "balanced" in medium.lower()
        assert "comprehensive" in detailed.lower()
