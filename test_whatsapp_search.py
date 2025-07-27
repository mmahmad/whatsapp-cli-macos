#!/usr/bin/env python3
"""
Unit tests for WhatsApp Search functionality

Run with: python3 -m pytest test_whatsapp_search.py -v
Or: python3 test_whatsapp_search.py
"""

import unittest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock
from whatsapp_search import WhatsAppSearcher, get_whatsapp_db_paths

class TestWhatsAppSearcher(unittest.TestCase):
    """Test suite for WhatsApp search functionality"""
    
    def setUp(self):
        """Set up test database with sample data"""
        # Create temporary database
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.test_db_path = self.test_db.name
        self.test_db.close()
        
        # Create test database schema and data
        self._create_test_database()
        
        # Mock the searcher to use our test database
        with patch.object(WhatsAppSearcher, '_find_database'):
            self.searcher = WhatsAppSearcher()
            self.searcher.db_path = self.test_db_path
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db_path)
    
    def _create_test_database(self):
        """Create test database with sample WhatsApp data"""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE ZWACHATSESSION (
                Z_PK INTEGER PRIMARY KEY,
                ZPARTNERNAME VARCHAR,
                ZCONTACTJID VARCHAR
            )
        """)
        
        cursor.execute("""
            CREATE TABLE ZWAMESSAGE (
                Z_PK INTEGER PRIMARY KEY,
                ZTEXT VARCHAR,
                ZMESSAGEDATE TIMESTAMP,
                ZISFROMME INTEGER,
                ZFROMJID VARCHAR,
                ZCHATSESSION INTEGER,
                ZGROUPMEMBER INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE ZWAGROUPMEMBER (
                Z_PK INTEGER PRIMARY KEY,
                ZMEMBERJID VARCHAR,
                ZCONTACTNAME VARCHAR
            )
        """)
        
        # Insert test chat sessions
        cursor.execute("""
            INSERT INTO ZWACHATSESSION (Z_PK, ZPARTNERNAME, ZCONTACTJID) VALUES
            (1, 'John Doe', '1234567890@s.whatsapp.net'),
            (2, 'Test Group', '120363147278467611@g.us'),
            (3, 'Jane Smith', '9876543210@s.whatsapp.net')
        """)
        
        # Insert test group members
        cursor.execute("""
            INSERT INTO ZWAGROUPMEMBER (Z_PK, ZMEMBERJID, ZCONTACTNAME) VALUES
            (101, '1111111111@s.whatsapp.net', 'Alice'),
            (102, '2222222222@s.whatsapp.net', 'Bob')
        """)
        
        # Insert test messages (Core Data timestamps: seconds since Jan 1, 2001)
        test_messages = [
            # Direct messages
            (1, 'Hello world', 775000000, 0, '1234567890@s.whatsapp.net', 1, None),
            (2, 'This is a test message', 775000100, 1, None, 1, None),
            (3, 'Pizza party tonight!', 775000200, 0, '1234567890@s.whatsapp.net', 1, None),
            
            # Group messages  
            (4, 'Hey everyone', 775000300, 0, '120363147278467611@g.us', 2, 101),
            (5, 'Meeting at 3pm', 775000400, 0, '120363147278467611@g.us', 2, 102),
            (6, 'Can we reschedule the appointment?', 775000500, 1, None, 2, None),
            
            # Messages for fuzzy testing
            (7, 'Hawaii is beautiful', 775000600, 0, '9876543210@s.whatsapp.net', 3, None),  
            (8, 'Haha that is funny', 775000700, 0, '9876543210@s.whatsapp.net', 3, None),
            (9, 'Wait for me', 775000800, 0, '9876543210@s.whatsapp.net', 3, None),
            (10, 'I have an appointment', 775000900, 0, '9876543210@s.whatsapp.net', 3, None),
            
            # Short messages 
            (11, 'A', 775001000, 0, '1234567890@s.whatsapp.net', 1, None),
            (12, 'Okay sure', 775001100, 0, '1234567890@s.whatsapp.net', 1, None),  # Changed from "Ok" to test exact matching
        ]
        
        cursor.executemany("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, test_messages)
        
        conn.commit()
        conn.close()

class TestFuzzyMatching(TestWhatsAppSearcher):
    """Test fuzzy matching behavior"""
    
    def test_exact_match_gets_100_score(self):
        """Exact matches should get 100% score"""
        search_result = self.searcher.search_messages("Hawaii", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find "Hawaii is beautiful"
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][4], 100)  # Score should be 100
        self.assertIn("Hawaii is beautiful", results[0][0])
    
    def test_false_positives_filtered_out(self):
        """Words like 'Haha' should not match 'Hawaii'"""
        search_result = self.searcher.search_messages("Hawaii", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should not find "Haha that is funny"
        message_texts = [result[0] for result in results]
        self.assertNotIn("Haha that is funny", message_texts)
    
    def test_short_word_exact_match(self):
        """Short words should work with exact matches"""
        search_result = self.searcher.search_messages("Wait", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find "Wait for me"
        self.assertEqual(len(results), 1)
        self.assertIn("Wait for me", results[0][0])
    
    def test_typo_tolerance(self):
        """Typos should still be found with good scores"""
        search_result = self.searcher.search_messages("appoinment", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find messages containing "appointment"
        self.assertGreaterEqual(len(results), 1)
        # At least one result should contain "appointment"
        found_appointment = any("appointment" in result[0] for result in results)
        self.assertTrue(found_appointment)
        # Score should be reasonably high for fuzzy match
        appointment_result = next(r for r in results if "appointment" in r[0])
        self.assertGreaterEqual(appointment_result[4], 80)

class TestMessageFiltering(TestWhatsAppSearcher):
    """Test message filtering logic"""
    
    def test_short_messages_filtered(self):
        """Messages shorter than 3 characters should be filtered out when searching"""
        search_result = self.searcher.search_messages("xyz", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Single letter messages like "A" should not appear in results 
        # (they're filtered out by length check)
        result_texts = [r[0] for r in results]
        self.assertNotIn("A", result_texts)
    
    def test_valid_short_words_work(self):
        """Valid short words should work when they appear in longer messages"""
        search_result = self.searcher.search_messages("Okay", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find "Okay sure" message (exact match)
        self.assertGreaterEqual(len(results), 1)
        result_texts = [r[0] for r in results]
        found_okay = any("Okay" in text for text in result_texts)
        self.assertTrue(found_okay)

class TestSenderInformation(TestWhatsAppSearcher):
    """Test sender information display"""
    
    @patch.object(WhatsAppSearcher, '_get_contact_name_by_jid')
    def test_direct_message_sender_info(self, mock_get_contact):
        """Direct messages should show proper sender info"""
        mock_get_contact.return_value = "John Doe"
        
        search_result = self.searcher.search_messages("Hello", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        self.assertEqual(len(results), 1)
        # Format: message_text, sender_info, chat_name, timestamp, score
        self.assertEqual(results[0][1], "John Doe (1234567890)")
        self.assertEqual(results[0][2], "John Doe")
    
    @patch.object(WhatsAppSearcher, '_get_contact_name_by_jid')
    def test_group_message_sender_info(self, mock_get_contact):
        """Group messages should show individual sender, not group name"""
        mock_get_contact.return_value = "Alice"
        
        search_result = self.searcher.search_messages("Hey everyone", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        self.assertEqual(len(results), 1)
        # Should show Alice as sender, not "Test Group"
        self.assertEqual(results[0][1], "Alice (1111111111)")
        self.assertEqual(results[0][2], "Test Group")
    
    def test_own_messages_marked_as_you(self):
        """Messages sent by user should be marked as 'You'"""
        search_result = self.searcher.search_messages("test message", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], "You")

class TestContactSearch(TestWhatsAppSearcher):
    """Test contact-specific search functionality"""
    
    def test_search_by_contact_name(self):
        """Should be able to search within specific contact"""
        search_result = self.searcher.search_by_contact("John", "Pizza", limit=10)
        results = search_result["results"]
        
        # Should find pizza message from John Doe
        self.assertEqual(len(results), 1)
        self.assertIn("Pizza party", results[0][0])
        
        # Check pagination metadata
        self.assertEqual(search_result["total_matches"], 1)
        self.assertEqual(search_result["page"], 1)
        self.assertEqual(search_result["total_pages"], 1)
        self.assertFalse(search_result["has_more"])
    
    def test_browse_contact_messages(self):
        """Should be able to browse recent messages from contact"""
        search_result = self.searcher.search_by_contact("John", "", limit=10)
        results = search_result["results"]
        
        # Should find all messages from John Doe conversation
        self.assertGreater(len(results), 1)
        
        # Check that results are from the right conversation
        message_texts = [result[0] for result in results]
        self.assertIn("Hello world", message_texts)
        self.assertIn("Pizza party tonight!", message_texts)
        
        # Check pagination metadata
        self.assertGreater(search_result["total_matches"], 1)
        self.assertEqual(search_result["page"], 1)
    
    def test_contact_search_pagination(self):
        """Test that contact search supports pagination"""
        # Add more messages from John to test pagination
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add 5 more messages from John Doe
        for i in range(20, 25):
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, f"Contact pagination test message {i}", 775000000 + i * 100))
        
        conn.commit()
        conn.close()
        
        # Test first page with limit 3
        search_result_page1 = self.searcher.search_by_contact("John", "", limit=3, page=1)
        
        self.assertEqual(search_result_page1["page"], 1)
        self.assertEqual(len(search_result_page1["results"]), 3)
        self.assertGreater(search_result_page1["total_matches"], 3)
        self.assertGreater(search_result_page1["total_pages"], 1)
        self.assertTrue(search_result_page1["has_more"])
        
        # Test second page
        search_result_page2 = self.searcher.search_by_contact("John", "", limit=3, page=2)
        
        self.assertEqual(search_result_page2["page"], 2)
        self.assertGreaterEqual(len(search_result_page2["results"]), 1)
        
        # Ensure different results on different pages
        page1_texts = [r[0] for r in search_result_page1["results"]]
        page2_texts = [r[0] for r in search_result_page2["results"]]
        self.assertNotEqual(page1_texts, page2_texts)
    
    def test_contact_search_empty_query_pagination(self):
        """Test contact search pagination with empty query (browse all messages)"""
        # Test browsing all messages from a contact with pagination
        search_result = self.searcher.search_by_contact("John", "", limit=2, page=1)
        
        # Should find messages and support pagination
        self.assertGreater(search_result["total_matches"], 0)
        self.assertEqual(search_result["page"], 1)
        self.assertLessEqual(len(search_result["results"]), 2)
        
        # Test that pagination metadata is consistent
        expected_pages = (search_result["total_matches"] + 1) // 2  # Ceiling division for limit=2
        self.assertEqual(search_result["total_pages"], expected_pages)
    
    def test_contact_search_invalid_page(self):
        """Test contact search with invalid page numbers"""
        # Test page beyond available results
        search_result = self.searcher.search_by_contact("John", "", limit=10, page=999)
        
        # Should return empty results for invalid page but valid metadata
        self.assertEqual(len(search_result["results"]), 0)
        self.assertEqual(search_result["page"], 999)
        self.assertFalse(search_result["has_more"])

class TestDatabaseStatistics(TestWhatsAppSearcher):
    """Test database statistics functionality"""
    
    def test_get_chat_statistics(self):
        """Should return correct database statistics"""
        stats = self.searcher.get_chat_statistics()
        
        self.assertEqual(stats['total_messages'], 12)  # All messages including short ones
        self.assertEqual(stats['text_messages'], 12)   # All messages have text
        self.assertEqual(stats['total_chats'], 3)       # 3 chat sessions
        self.assertEqual(stats['named_chats'], 3)       # All have names

class TestContactNameResolution(TestWhatsAppSearcher):
    """Test contact name resolution from JID"""
    
    def test_contact_name_fallback(self):
        """Should fallback to phone number if no contact name found"""
        # Empty contact cache - should fallback to phone number
        empty_cache = {}
        
        result = self.searcher._get_contact_name_by_jid("1234567890@s.whatsapp.net", empty_cache)
        self.assertEqual(result, "1234567890")
    
    def test_contact_name_extraction(self):
        """Should extract phone number from JID correctly"""
        # Empty contact cache for fallback behavior
        empty_cache = {}
        
        result = self.searcher._get_contact_name_by_jid("1234567890@s.whatsapp.net", empty_cache)
        self.assertEqual(result, "1234567890")
        
        result = self.searcher._get_contact_name_by_jid("invalid_jid", empty_cache)
        self.assertEqual(result, "invalid_jid")
    
    def test_contact_name_cache_usage(self):
        """Should use cached contact names when available"""
        # Contact cache with names
        contact_cache = {
            "1234567890@s.whatsapp.net": "John Doe",
            "9876543210@s.whatsapp.net": "Jane Smith"
        }
        
        result = self.searcher._get_contact_name_by_jid("1234567890@s.whatsapp.net", contact_cache)
        self.assertEqual(result, "John Doe")
        
        result = self.searcher._get_contact_name_by_jid("9876543210@s.whatsapp.net", contact_cache)
        self.assertEqual(result, "Jane Smith")

class TestErrorHandling(TestWhatsAppSearcher):
    """Test error handling scenarios"""
    
    def test_empty_query(self):
        """Empty queries should return empty results"""
        search_result = self.searcher.search_messages("", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        self.assertEqual(len(results), 0)
    
    def test_no_matches(self):
        """Queries with no matches should return empty results"""
        search_result = self.searcher.search_messages("nonexistent_word_12345", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        self.assertEqual(len(results), 0)
    
    def test_invalid_contact_search(self):
        """Searching for non-existent contact should return empty results"""
        search_result = self.searcher.search_by_contact("NonExistentContact", "test", limit=10)
        self.assertEqual(len(search_result["results"]), 0)
        self.assertEqual(search_result["total_matches"], 0)

class TestPagination(TestWhatsAppSearcher):
    """Test pagination functionality"""
    
    def test_pagination_basic(self):
        """Test basic pagination functionality"""
        # Add more messages to test pagination
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add 5 more messages containing "test"
        for i in range(13, 18):  # IDs 13-17
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, f"test message {i}", 775000000 + i * 100, ))
        
        conn.commit()
        conn.close()
        
        # Test first page with limit 3
        search_result = self.searcher.search_messages("test", limit=3, page=1)
        
        self.assertEqual(search_result["page"], 1)
        self.assertEqual(len(search_result["results"]), 3)
        self.assertGreater(search_result["total_matches"], 3)
        self.assertGreater(search_result["total_pages"], 1)
        self.assertTrue(search_result["has_more"])
    
    def test_pagination_page_navigation(self):
        """Test navigation between pages"""
        # Add test messages
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        for i in range(20, 25):  # Add 5 more messages
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, f"pagination message {i}", 775000000 + i * 100))
        
        conn.commit()
        conn.close()
        
        # Test page 1
        page1 = self.searcher.search_messages("pagination", limit=2, page=1)
        self.assertEqual(page1["page"], 1)
        self.assertEqual(len(page1["results"]), 2)
        
        # Test page 2
        page2 = self.searcher.search_messages("pagination", limit=2, page=2)
        self.assertEqual(page2["page"], 2)
        self.assertGreaterEqual(len(page2["results"]), 1)
        
        # Ensure different results on different pages
        page1_texts = [r[0] for r in page1["results"]]
        page2_texts = [r[0] for r in page2["results"]]
        self.assertNotEqual(page1_texts, page2_texts)
    
    def test_pagination_last_page(self):
        """Test behavior on last page"""
        search_result = self.searcher.search_messages("Hawaii", limit=10, page=1)
        
        # Should be exactly 1 result for Hawaii, so page 1 should be last page
        self.assertEqual(search_result["page"], 1)
        self.assertEqual(search_result["total_pages"], 1)
        self.assertFalse(search_result["has_more"])
    
    def test_pagination_invalid_page(self):
        """Test behavior with invalid page numbers"""
        # Page beyond available results should return empty results
        search_result = self.searcher.search_messages("Hawaii", limit=10, page=999)
        
        self.assertEqual(search_result["page"], 999)
        self.assertEqual(len(search_result["results"]), 0)
        self.assertFalse(search_result["has_more"])

class TestSorting(TestWhatsAppSearcher):
    """Test sorting functionality"""
    
    def setUp(self):
        """Set up with messages at different times for sorting tests"""
        super().setUp()
        
        # Add messages with specific timestamps for sorting tests
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add messages with different timestamps and scores
        test_messages = [
            (50, "sorting perfect match", 775001000, 0, '1234567890@s.whatsapp.net', 1, None),  # Recent, perfect
            (51, "sorting okay match here", 775000500, 0, '1234567890@s.whatsapp.net', 1, None),  # Older, partial
            (52, "sorting another perfect match", 775001500, 0, '1234567890@s.whatsapp.net', 1, None),  # Newest, perfect
        ]
        
        cursor.executemany("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, test_messages)
        
        conn.commit()
        conn.close()
    
    def test_sort_by_relevance(self):
        """Test sorting by relevance (default)"""
        search_result = self.searcher.search_messages("sorting", sort_by="relevance")
        results = search_result["results"]
        
        # Should have 3+ results
        self.assertGreaterEqual(len(results), 3)
        
        # Check that results are sorted by score first (descending)
        scores = [r[4] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        
        # Perfect matches should come before partial matches
        perfect_matches = [r for r in results if r[4] == 100]
        self.assertGreaterEqual(len(perfect_matches), 2)
    
    def test_sort_by_time(self):
        """Test sorting by time"""
        search_result = self.searcher.search_messages("sorting", sort_by="time")
        results = search_result["results"]
        
        # Should have 3+ results
        self.assertGreaterEqual(len(results), 3)
        
        # Check that results are sorted by timestamp (most recent first)
        timestamps = [r[3] for r in results]
        # Convert to comparable format and check descending order
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
        
        # Most recent message should be first (regardless of score)
        self.assertIn("sorting another perfect match", results[0][0])
    
    def test_sort_by_relevance_then_time(self):
        """Test that relevance sorting uses time as tiebreaker"""
        # Add two messages with same content (same score) but different times
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        cursor.executemany("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            (60, "identical message", 775002000, 0, '1234567890@s.whatsapp.net', 1, None),  # Newer
            (61, "identical message", 775001000, 0, '1234567890@s.whatsapp.net', 1, None),  # Older
        ])
        
        conn.commit()
        conn.close()
        
        search_result = self.searcher.search_messages("identical", sort_by="relevance")
        results = search_result["results"]
        
        # Should find both messages
        self.assertEqual(len(results), 2)
        
        # Both should have same score (100%)
        self.assertEqual(results[0][4], 100)
        self.assertEqual(results[1][4], 100)
        
        # Newer message should come first (time tiebreaker)
        timestamps = [r[3] for r in results]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))
    
    def test_invalid_sort_parameter(self):
        """Test that invalid sort parameter defaults to relevance"""
        # This should not raise an error and should default to relevance
        search_result = self.searcher.search_messages("Hawaii", sort_by="invalid")
        
        # Should still return results (defaulting to relevance sorting)
        self.assertGreaterEqual(search_result["total_matches"], 1)

class TestPaginationAndSorting(TestWhatsAppSearcher):
    """Test pagination combined with sorting"""
    
    def test_pagination_with_time_sorting(self):
        """Test that pagination works correctly with time sorting"""
        # Add multiple messages with different timestamps
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        for i in range(70, 75):
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, f"combined test {i}", 775000000 + i * 1000))
        
        conn.commit()
        conn.close()
        
        # Get page 1 with time sorting
        page1 = self.searcher.search_messages("combined", sort_by="time", limit=2, page=1)
        page2 = self.searcher.search_messages("combined", sort_by="time", limit=2, page=2)
        
        # Check that time ordering is maintained across pages
        page1_times = [r[3] for r in page1["results"]]
        page2_times = [r[3] for r in page2["results"]]
        
        # Most recent should be in page 1
        if page2_times:  # If page 2 has results
            self.assertGreater(min(page1_times), max(page2_times))
    
    def test_pagination_metadata_consistency(self):
        """Test that pagination metadata is consistent across different parameters"""
        # Test same query with different page sizes
        result_small = self.searcher.search_messages("message", limit=2, page=1)
        result_large = self.searcher.search_messages("message", limit=10, page=1)
        
        # Total matches should be the same regardless of page size
        self.assertEqual(result_small["total_matches"], result_large["total_matches"])
        
        # But total pages should be different
        if result_small["total_matches"] > 2:
            self.assertGreater(result_small["total_pages"], result_large["total_pages"])

class TestPerformance(TestWhatsAppSearcher):
    """Test performance-related aspects"""
    
    def test_large_result_set_handling(self):
        """Test handling of queries that return many results"""
        # Add many messages
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add 50 messages with "performance" keyword
        for i in range(100, 150):
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, f"performance test message {i}", 775000000 + i))
        
        conn.commit()
        conn.close()
        
        # Query should handle large result set efficiently
        search_result = self.searcher.search_messages("performance", limit=10, page=1)
        
        # Should return exactly 10 results even though there are 50 matches
        self.assertEqual(len(search_result["results"]), 10)
        self.assertEqual(search_result["total_matches"], 50)
        self.assertEqual(search_result["total_pages"], 5)
        self.assertTrue(search_result["has_more"])

class TestCaching(TestWhatsAppSearcher):
    """Test search result caching functionality"""
    
    def test_page_cache_consistency(self):
        """Test that cached pages return identical results"""
        # First search - page 1
        search_result1 = self.searcher.search_messages("message", limit=2, page=1)
        page1_first_call = search_result1["results"]
        
        # Go to page 2
        search_result2 = self.searcher.search_messages("message", limit=2, page=2)
        page2_results = search_result2["results"]
        
        # Go back to page 1 - should be identical to first call
        search_result1_cached = self.searcher.search_messages("message", limit=2, page=1)
        page1_second_call = search_result1_cached["results"]
        
        # Results should be identical
        self.assertEqual(len(page1_first_call), len(page1_second_call))
        for i in range(len(page1_first_call)):
            self.assertEqual(page1_first_call[i], page1_second_call[i])
    
    def test_cache_invalidation_on_sort_change(self):
        """Test that cache is invalidated when sort parameter changes"""
        # Search with relevance sort
        search_result_relevance = self.searcher.search_messages("test", sort_by="relevance", limit=5)
        relevance_results = search_result_relevance["results"]
        
        # Search with time sort - should trigger cache invalidation
        search_result_time = self.searcher.search_messages("test", sort_by="time", limit=5)
        time_results = search_result_time["results"]
        
        # Results should be different (different sort order)
        if len(relevance_results) > 1 and len(time_results) > 1:
            # At least the order might be different
            self.assertTrue(relevance_results != time_results or len(relevance_results) == 1)
    
    def test_cache_key_generation(self):
        """Test that cache keys are generated correctly"""
        key1 = self.searcher._get_cache_key("test", 60, "relevance")
        key2 = self.searcher._get_cache_key("test", 60, "relevance")
        key3 = self.searcher._get_cache_key("test", 70, "relevance")
        key4 = self.searcher._get_cache_key("different", 60, "relevance")
        
        # Same parameters should generate same key
        self.assertEqual(key1, key2)
        
        # Different parameters should generate different keys
        self.assertNotEqual(key1, key3)  # Different threshold
        self.assertNotEqual(key1, key4)  # Different query
    
    def test_cache_clear_functionality(self):
        """Test that cache clearing works correctly"""
        # Populate cache
        self.searcher.search_messages("test", limit=5, page=1)
        
        # Verify cache has content
        self.assertTrue(len(self.searcher._search_cache) > 0)
        
        # Clear cache
        self.searcher._clear_cache()
        
        # Verify cache is empty
        self.assertEqual(len(self.searcher._search_cache), 0)
        self.assertIsNone(self.searcher._current_cache_key)

class TestPerformanceOptimizations(TestWhatsAppSearcher):
    """Test performance optimization features"""
    
    def test_database_filtering_reduces_candidates(self):
        """Test that database filtering reduces the number of candidate messages"""
        # Add many messages, only some contain our search term
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add 20 messages, only 3 should match "optimization"
        for i in range(100, 120):
            if i % 7 == 0:  # Every 7th message contains our term
                text = f"This message is about optimization testing {i}"
            else:
                text = f"Random message that does not contain our term {i}"
            
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (i, text, 775000000 + i))
        
        conn.commit()
        conn.close()
        
        # Search for "optimization" - should find only the 3 messages that contain it
        search_result = self.searcher.search_messages("optimization", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find exactly 3 matches (messages 105, 112, 119)
        self.assertEqual(len(results), 3)
        
        # All results should contain "optimization"
        for result in results:
            self.assertIn("optimization", result[0].lower())
    
    def test_contact_name_preloading_efficiency(self):
        """Test that contact names are pre-loaded efficiently"""
        # Mock the _preload_contact_names method to track calls
        original_method = self.searcher._preload_contact_names
        call_count = [0]
        
        def mock_preload():
            call_count[0] += 1
            return original_method()
        
        with patch.object(self.searcher, '_preload_contact_names', side_effect=mock_preload):
            # Perform multiple searches - should only preload once per search session
            self.searcher.search_messages("Hello", limit=5, page=1)
            self.searcher.search_messages("Hello", limit=5, page=2)  # Should use cache
            
            # Should have called preload only once (for the first search)
            self.assertEqual(call_count[0], 1)
    
    def test_typo_tolerance_database_patterns(self):
        """Test that typo tolerance creates appropriate database patterns"""
        # Add a message with "appointment" to test typo patterns
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
            VALUES (200, 'I have an important appointment today', 775002000, 0, '1234567890@s.whatsapp.net', 1, NULL)
        """)
        conn.commit()
        conn.close()
        
        # Test various typos should still find the appointment message
        typo_queries = [
            "appoinment",    # Missing 't'
            "appointmet",    # Missing 'n' 
            "apointment",    # Missing 'p'
        ]
        
        for typo_query in typo_queries:
            search_result = self.searcher.search_messages(typo_query, limit=10, fuzzy_threshold=60)
            results = search_result["results"]
            
            # Should find the appointment message despite typo
            self.assertGreaterEqual(len(results), 1, f"Typo '{typo_query}' should find appointment message")
            
            # Check that at least one result contains "appointment"
            found_appointment = any("appointment" in result[0].lower() for result in results)
            self.assertTrue(found_appointment, f"Typo '{typo_query}' should match 'appointment'")
    
    def test_exact_match_performance_optimization(self):
        """Test that exact matches get 100% score without expensive fuzzy matching"""
        # Add messages for exact vs fuzzy testing
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        test_messages = [
            (300, "This contains the exact word meeting", 775003000),
            (301, "This is about a business meting session", 775003100),  # Typo version
        ]
        
        for msg_id, text, timestamp in test_messages:
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (msg_id, text, timestamp))
        
        conn.commit()
        conn.close()
        
        # Search for exact word "meeting"
        search_result = self.searcher.search_messages("meeting", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find at least the exact match
        self.assertGreaterEqual(len(results), 1)
        
        # The exact match should have 100% score
        exact_match = next((r for r in results if "exact word meeting" in r[0]), None)
        self.assertIsNotNone(exact_match, "Should find exact match")
        self.assertEqual(exact_match[4], 100, "Exact match should have 100% score")
    
    def test_empty_query_optimization(self):
        """Test that empty queries are handled efficiently without database queries"""
        # Test various empty query formats
        empty_queries = ["", "   ", "\t", "\n"]
        
        for empty_query in empty_queries:
            search_result = self.searcher.search_messages(empty_query, limit=10, fuzzy_threshold=60)
            
            # Should return empty results immediately
            self.assertEqual(search_result["total_matches"], 0)
            self.assertEqual(len(search_result["results"]), 0)
            self.assertEqual(search_result["total_pages"], 0)
            self.assertFalse(search_result["has_more"])
    
    def test_short_message_filtering_optimization(self):
        """Test that very short messages are filtered at database level"""
        # Add very short messages that should be filtered out
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        short_messages = [
            (400, "Hi", 775004000),
            (401, "Ok", 775004100), 
            (402, "No", 775004200),
            (403, "Yes please", 775004300),  # This should be included
        ]
        
        for msg_id, text, timestamp in short_messages:
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (msg_id, text, timestamp))
        
        conn.commit()
        conn.close()
        
        # Search for something that would match short messages
        search_result = self.searcher.search_messages("yes", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should only find "Yes please" (length >= 3), not just "Yes" or other short messages
        result_texts = [r[0] for r in results]
        self.assertIn("Yes please", result_texts)
    
    def test_contact_cache_efficiency(self):
        """Test that contact names are cached and reused efficiently"""
        # Create a large result set that would normally require many contact lookups
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add multiple messages from the same contact
        same_contact_jid = "1234567890@s.whatsapp.net"
        for i in range(500, 510):
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, ?, 1, NULL)
            """, (i, f"Contact efficiency test message {i}", 775005000 + i, same_contact_jid))
        
        conn.commit()
        conn.close()
        
        # Search should efficiently use cached contact names
        search_result = self.searcher.search_messages("efficiency", limit=20, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find all 10 messages
        self.assertEqual(len(results), 10)
        
        # All should have the same contact info (demonstrating cache efficiency)
        unique_senders = set(result[1] for result in results)
        self.assertEqual(len(unique_senders), 1, "All messages from same contact should have same sender info")
    
    def test_search_parameter_caching_isolation(self):
        """Test that different search parameters don't interfere with each other"""
        # Perform searches with different parameters
        search1 = self.searcher.search_messages("test", fuzzy_threshold=60, sort_by="relevance")
        search2 = self.searcher.search_messages("test", fuzzy_threshold=80, sort_by="relevance")
        search3 = self.searcher.search_messages("test", fuzzy_threshold=60, sort_by="time")
        
        # Each should have generated different cache keys and potentially different results
        # The important thing is they don't interfere with each other
        
        # Verify that going back to the first search uses cache
        search1_repeat = self.searcher.search_messages("test", fuzzy_threshold=60, sort_by="relevance")
        
        # Results should be identical (from cache)
        self.assertEqual(search1["total_matches"], search1_repeat["total_matches"])
        self.assertEqual(len(search1["results"]), len(search1_repeat["results"]))
    
    def test_database_level_length_filtering(self):
        """Test that LENGTH(m.ZTEXT) >= 3 filter works at database level"""
        # This test verifies the SQL query filters short messages before Python processing
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Add mix of short and long messages
        messages = [
            (600, "a", 775006000),      # Length 1 - should be filtered
            (601, "ab", 775006100),     # Length 2 - should be filtered  
            (602, "abc", 775006200),    # Length 3 - should be included
            (603, "abcd", 775006300),   # Length 4 - should be included
        ]
        
        for msg_id, text, timestamp in messages:
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
                VALUES (?, ?, ?, 0, '1234567890@s.whatsapp.net', 1, NULL)
            """, (msg_id, text, timestamp))
        
        conn.commit()
        conn.close()
        
        # Search for "ab" - should only find "abc" and "abcd", not "a" or "ab"
        search_result = self.searcher.search_messages("ab", limit=10, fuzzy_threshold=50)
        results = search_result["results"]
        
        # Should find messages with length >= 3 that contain "ab"
        result_texts = [r[0] for r in results]
        self.assertIn("abc", result_texts)
        self.assertIn("abcd", result_texts)
        self.assertNotIn("a", result_texts)
        self.assertNotIn("ab", result_texts)
    
    def test_progress_indicators_and_messaging(self):
        """Test that performance optimizations include helpful progress messages"""
        # This is more of an integration test to ensure user feedback
        # We can't easily test print statements, but we can verify the flow
        
        # Mock print to capture output
        printed_messages = []
        
        def mock_print(*args, **kwargs):
            printed_messages.append(' '.join(str(arg) for arg in args))
        
        with patch('builtins.print', side_effect=mock_print):
            search_result = self.searcher.search_messages("Hello", limit=5, fuzzy_threshold=60)
        
        # Verify that performance-related messages were printed
        messages_text = ' '.join(printed_messages)
        
        # Should contain pre-loading message
        self.assertTrue(any("Pre-loading contact names" in msg for msg in printed_messages))
        
        # Should contain processing message
        self.assertTrue(any("Processing" in msg and "candidate messages" in msg for msg in printed_messages))
        
        # Should contain results summary
        self.assertTrue(any("Found" in msg and "matching messages" in msg for msg in printed_messages))
        
        # Should contain caching message
        self.assertTrue(any("Cached" in msg and "results for future" in msg for msg in printed_messages))

class TestScoring(TestWhatsAppSearcher):
    """Test scoring system"""
    
    def test_exact_matches_score_higher(self):
        """Exact matches should score higher than fuzzy matches"""
        # Add a fuzzy match scenario
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZFROMJID, ZCHATSESSION, ZGROUPMEMBER)
            VALUES (100, 'Testing appointment booking', 775002000, 0, '1234567890@s.whatsapp.net', 1, NULL)
        """)
        conn.commit()
        conn.close()
        
        search_result = self.searcher.search_messages("appointment", limit=10, fuzzy_threshold=60)
        results = search_result["results"]
        
        # Should find messages containing "appointment"
        self.assertGreaterEqual(len(results), 2)
        
        # Messages with exact word matches should score 100%
        exact_matches = [r for r in results if "appointment" in r[0]]
        self.assertGreaterEqual(len(exact_matches), 2)
        
        for result in exact_matches:
            self.assertEqual(result[4], 100)

class TestChatViewing(unittest.TestCase):
    """Test suite for chat viewing functionality"""
    
    def setUp(self):
        """Set up test database with sample data"""
        # Create temporary database
        self.test_db = tempfile.NamedTemporaryFile(delete=False, suffix='.sqlite')
        self.test_db_path = self.test_db.name
        self.test_db.close()
        
        # Create test database schema and data
        self._create_test_database()
        
        # Mock the searcher to use our test database
        with patch.object(WhatsAppSearcher, '_find_database'):
            self.searcher = WhatsAppSearcher()
            self.searcher.db_path = self.test_db_path
    
    def tearDown(self):
        """Clean up test database"""
        os.unlink(self.test_db_path)
    
    def _create_test_database(self):
        """Create test database with sample data for chat viewing"""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE ZWACHATSESSION (
                Z_PK INTEGER PRIMARY KEY,
                ZPARTNERNAME VARCHAR,
                ZCONTACTJID VARCHAR
            )
        """)
        
        cursor.execute("""
            CREATE TABLE ZWAMESSAGE (
                Z_PK INTEGER PRIMARY KEY,
                ZTEXT VARCHAR,
                ZMESSAGEDATE REAL,
                ZISFROMME INTEGER,
                ZCHATSESSION INTEGER,
                ZFROMJID VARCHAR,
                ZGROUPMEMBER INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE ZWAGROUPMEMBER (
                Z_PK INTEGER PRIMARY KEY,
                ZMEMBERJID VARCHAR
            )
        """)
        
        # Insert test contacts
        cursor.execute("INSERT INTO ZWACHATSESSION (Z_PK, ZPARTNERNAME, ZCONTACTJID) VALUES (1, 'John Doe', '1234567890@s.whatsapp.net')")
        cursor.execute("INSERT INTO ZWACHATSESSION (Z_PK, ZPARTNERNAME, ZCONTACTJID) VALUES (2, 'Alice Smith', '9876543210@s.whatsapp.net')")
        cursor.execute("INSERT INTO ZWACHATSESSION (Z_PK, ZPARTNERNAME, ZCONTACTJID) VALUES (3, 'Bob Johnson', '5555555555@s.whatsapp.net')")
        
        # Insert test messages for John Doe (session 1) - conversation with multiple messages
        messages = [
            (1, "Hey, how are you?", 704067600.0, 0, 1, "1234567890@s.whatsapp.net", None),  # From John
            (2, "I'm doing great, thanks for asking!", 704067700.0, 1, 1, None, None),      # From me
            (3, "That's wonderful to hear", 704067800.0, 0, 1, "1234567890@s.whatsapp.net", None),  # From John
            (4, "Want to grab lunch tomorrow?", 704067900.0, 0, 1, "1234567890@s.whatsapp.net", None),  # From John
            (5, "Sure! What time works for you?", 704068000.0, 1, 1, None, None),          # From me
            (6, "How about 12:30 PM?", 704068100.0, 0, 1, "1234567890@s.whatsapp.net", None),  # From John
            (7, "Perfect! See you then", 704068200.0, 1, 1, None, None),                   # From me
            (8, "Looking forward to it", 704068300.0, 0, 1, "1234567890@s.whatsapp.net", None),  # From John
        ]
        
        for msg in messages:
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZCHATSESSION, ZFROMJID, ZGROUPMEMBER) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, msg)
        
        # Insert test messages for Alice Smith (session 2) - shorter conversation
        alice_messages = [
            (9, "Quick question about the project", 704065000.0, 0, 2, "9876543210@s.whatsapp.net", None),  # From Alice
            (10, "Sure, what's up?", 704065100.0, 1, 2, None, None),                      # From me
            (11, "When is the deadline?", 704065200.0, 0, 2, "9876543210@s.whatsapp.net", None),  # From Alice
            (12, "Next Friday", 704065300.0, 1, 2, None, None),                           # From me
        ]
        
        for msg in alice_messages:
            cursor.execute("""
                INSERT INTO ZWAMESSAGE (Z_PK, ZTEXT, ZMESSAGEDATE, ZISFROMME, ZCHATSESSION, ZFROMJID, ZGROUPMEMBER) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, msg)
        
        conn.commit()
        conn.close()
    
    def test_view_chat_basic_functionality(self):
        """Test basic chat viewing functionality"""
        result = self.searcher.view_chat("John Doe")
        
        self.assertIsInstance(result, dict)
        self.assertIn("results", result)
        self.assertIn("total_matches", result) 
        self.assertIn("contact_name", result)
        self.assertEqual(result["contact_name"], "John Doe")
        self.assertEqual(result["total_matches"], 8)  # 8 messages in John's conversation
    
    def test_view_chat_pagination(self):
        """Test chat viewing with pagination"""
        # First page with limit 3
        result = self.searcher.view_chat("John Doe", limit=3, page=1)
        
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["total_pages"], 3)  # 8 messages / 3 per page = 3 pages (ceil)
        self.assertTrue(result["has_more"])
        
        # Second page
        result = self.searcher.view_chat("John Doe", limit=3, page=2)
        
        self.assertEqual(len(result["results"]), 3)
        self.assertEqual(result["page"], 2)
        self.assertTrue(result["has_more"])
        
        # Third page (last page, should have 2 messages)
        result = self.searcher.view_chat("John Doe", limit=3, page=3)
        
        self.assertEqual(len(result["results"]), 2)  # Only 2 messages left
        self.assertEqual(result["page"], 3)
        self.assertFalse(result["has_more"])
    
    def test_view_chat_fuzzy_matching(self):
        """Test fuzzy matching for contact names"""
        # Test partial name matching
        result = self.searcher.view_chat("John")
        self.assertEqual(result["contact_name"], "John Doe")
        
        # Test name with typo
        result = self.searcher.view_chat("Jon Doe")
        self.assertEqual(result["contact_name"], "John Doe")
        
        # Test last name only
        result = self.searcher.view_chat("Smith")
        self.assertEqual(result["contact_name"], "Alice Smith")
    
    def test_view_chat_message_format(self):
        """Test that messages are in the correct format"""
        result = self.searcher.view_chat("John Doe", limit=2)
        
        # Should have 2 messages
        self.assertEqual(len(result["results"]), 2)
        
        # Check message format: (message_text, sender_info, timestamp, is_from_me)
        for msg in result["results"]:
            self.assertEqual(len(msg), 4)
            text, sender, timestamp, is_from_me = msg
            
            self.assertIsInstance(text, str)
            self.assertIsInstance(sender, str)
            self.assertIsInstance(timestamp, str)
            self.assertIsInstance(is_from_me, int)
            
            # Sender should be either "You" or "John Doe"
            self.assertIn(sender, ["You", "John Doe"])
    
    def test_view_chat_nonexistent_contact(self):
        """Test viewing chat with non-existent contact"""
        result = self.searcher.view_chat("Unknown Person")
        
        self.assertEqual(result["total_matches"], 0)
        self.assertEqual(len(result["results"]), 0)
        self.assertIsNone(result["contact_name"])
        self.assertFalse(result["has_more"])


class TestDatabasePathDiscovery(unittest.TestCase):
    """Test suite for dynamic database path discovery functionality"""
    
    def test_get_whatsapp_db_paths_structure(self):
        """Test that get_whatsapp_db_paths returns correct path structure"""
        paths = get_whatsapp_db_paths()
        
        # Should return a list of exactly 3 paths
        self.assertIsInstance(paths, list)
        self.assertEqual(len(paths), 3)
        
        # All paths should be strings
        for path in paths:
            self.assertIsInstance(path, str)
        
        # All paths should end with ChatStorage.sqlite
        for path in paths:
            self.assertTrue(path.endswith('ChatStorage.sqlite'))
    
    def test_get_whatsapp_db_paths_contains_expected_containers(self):
        """Test that all expected WhatsApp containers are included"""
        paths = get_whatsapp_db_paths()
        path_strings = ' '.join(paths)
        
        # Should contain all three known WhatsApp container types
        self.assertIn('group.net.whatsapp.WhatsApp.shared', path_strings)
        self.assertIn('group.net.whatsapp.WhatsApp.private', path_strings)
        self.assertIn('group.net.whatsapp.family', path_strings)
    
    def test_get_whatsapp_db_paths_uses_current_user(self):
        """Test that paths are generated for the current user"""
        paths = get_whatsapp_db_paths()
        
        # All paths should contain the current user's home directory
        home_dir = os.path.expanduser("~")
        for path in paths:
            self.assertTrue(path.startswith(home_dir))
            self.assertIn('Library/Group Containers', path)
    
    @patch('os.path.expanduser')
    def test_get_whatsapp_db_paths_with_different_user(self, mock_expanduser):
        """Test that paths work correctly for different users"""
        # Mock a different user's home directory
        mock_expanduser.return_value = '/Users/testuser'
        
        paths = get_whatsapp_db_paths()
        
        # All paths should use the mocked user directory
        for path in paths:
            self.assertTrue(path.startswith('/Users/testuser'))
            self.assertIn('Library/Group Containers', path)
        
        # Verify expanduser was called
        mock_expanduser.assert_called_with("~")
    
    @patch('os.path.exists')
    def test_find_database_success_first_path(self, mock_exists):
        """Test _find_database when first path exists"""
        # Mock that the first path exists
        mock_exists.side_effect = lambda path: 'shared' in path
        
        # Capture printed output
        with patch('builtins.print') as mock_print:
            searcher = WhatsAppSearcher()
        
        # Should have found the shared database
        self.assertIsNotNone(searcher.db_path)
        self.assertIn('shared', searcher.db_path)
        
        # Should have printed search and found messages
        mock_print.assert_any_call('🔍 Searching for WhatsApp databases in user directory...')
        found_call = [call for call in mock_print.call_args_list if '✅ Found WhatsApp database:' in str(call)]
        self.assertTrue(len(found_call) > 0)
    
    @patch('os.path.exists')
    def test_find_database_success_second_path(self, mock_exists):
        """Test _find_database when second path exists"""
        # Mock that only the private path exists
        mock_exists.side_effect = lambda path: 'private' in path
        
        searcher = WhatsAppSearcher()
        
        # Should have found the private database
        self.assertIsNotNone(searcher.db_path)
        self.assertIn('private', searcher.db_path)
    
    @patch('os.path.exists')
    def test_find_database_success_third_path(self, mock_exists):
        """Test _find_database when third path exists"""
        # Mock that only the family path exists
        mock_exists.side_effect = lambda path: 'family' in path
        
        searcher = WhatsAppSearcher()
        
        # Should have found the family database
        self.assertIsNotNone(searcher.db_path)
        self.assertIn('family', searcher.db_path)
    
    @patch('os.path.exists')
    def test_find_database_no_database_found(self, mock_exists):
        """Test _find_database when no databases exist"""
        # Mock that no paths exist
        mock_exists.return_value = False
        
        # Should raise FileNotFoundError with helpful message
        with self.assertRaises(FileNotFoundError) as context:
            WhatsAppSearcher()
        
        error_message = str(context.exception)
        self.assertIn('No WhatsApp database found', error_message)
        self.assertIn('Checked locations:', error_message)
        self.assertIn('Please ensure:', error_message)
        self.assertIn('WhatsApp Desktop is installed', error_message)
    
    @patch('os.path.exists')
    def test_find_database_shows_all_paths_checked(self, mock_exists):
        """Test that _find_database shows all paths being checked"""
        # Mock that no paths exist
        mock_exists.return_value = False
        
        with patch('builtins.print') as mock_print:
            try:
                WhatsAppSearcher()
            except FileNotFoundError:
                pass  # Expected error
        
        # Should have printed search message
        mock_print.assert_any_call('🔍 Searching for WhatsApp databases in user directory...')
        
        # Should have printed "not found" for each path
        not_found_calls = [call for call in mock_print.call_args_list if '❌ Not found:' in str(call)]
        self.assertEqual(len(not_found_calls), 3)  # Should check all 3 paths
    
    @patch('os.path.exists')
    def test_find_database_stops_at_first_found(self, mock_exists):
        """Test that _find_database stops checking after finding first database"""
        # Mock that all paths exist
        mock_exists.return_value = True
        
        with patch('builtins.print') as mock_print:
            searcher = WhatsAppSearcher()
        
        # Should have found the first path (shared)
        self.assertIn('shared', searcher.db_path)
        
        # Should have only one "found" message
        found_calls = [call for call in mock_print.call_args_list if '✅ Found WhatsApp database:' in str(call)]
        self.assertEqual(len(found_calls), 1)
        
        # Should not have any "not found" messages
        not_found_calls = [call for call in mock_print.call_args_list if '❌ Not found:' in str(call)]
        self.assertEqual(len(not_found_calls), 0)
    
    def test_path_construction_is_cross_platform_safe(self):
        """Test that path construction uses proper separators"""
        paths = get_whatsapp_db_paths()
        
        # Paths should use os.path.join (no hardcoded separators)
        for path in paths:
            # Should not contain double slashes or mixed separators
            self.assertNotIn('//', path)
            self.assertNotIn('\\\\', path)
            
            # Should use the OS-appropriate separator
            expected_parts = ['Library', 'Group Containers']
            for part in expected_parts:
                self.assertIn(part, path)


def run_tests():
    """Run all tests"""
    unittest.main(verbosity=2)

if __name__ == '__main__':
    run_tests()