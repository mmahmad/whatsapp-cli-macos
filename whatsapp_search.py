#!/usr/bin/env python3
"""
WhatsApp Message Fuzzy Search Tool

This script provides fuzzy search functionality for WhatsApp messages stored on macOS.
It reads from the WhatsApp SQLite databases and allows searching through message content.
"""

import sqlite3
import sys
import argparse
from datetime import datetime
from typing import List, Tuple, Optional
from fuzzywuzzy import fuzz, process
import os

# WhatsApp database paths (dynamically generated for current user)
def get_whatsapp_db_paths():
    """Get WhatsApp database paths for the current user."""
    home_dir = os.path.expanduser("~")
    base_path = os.path.join(home_dir, "Library", "Group Containers")
    
    return [
        os.path.join(base_path, "group.net.whatsapp.WhatsApp.shared", "ChatStorage.sqlite"),
        os.path.join(base_path, "group.net.whatsapp.WhatsApp.private", "ChatStorage.sqlite"),
        os.path.join(base_path, "group.net.whatsapp.family", "ChatStorage.sqlite")
    ]

WHATSAPP_DB_PATHS = get_whatsapp_db_paths()

class WhatsAppSearcher:
    def __init__(self):
        self.db_path = None
        self._find_database()
        # Cache for search results to ensure page consistency
        self._search_cache = {}
        self._current_cache_key = None
    
    def _find_database(self):
        """Find the main WhatsApp database."""
        print(f"🔍 Searching for WhatsApp databases in user directory...")
        
        for path in WHATSAPP_DB_PATHS:
            if os.path.exists(path):
                self.db_path = path
                print(f"✅ Found WhatsApp database: {path}")
                break
            else:
                print(f"❌ Not found: {path}")
        
        if not self.db_path:
            home_dir = os.path.expanduser("~")
            error_msg = (
                f"No WhatsApp database found. Checked locations:\n"
                f"  - {home_dir}/Library/Group Containers/group.net.whatsapp.WhatsApp.shared/\n"
                f"  - {home_dir}/Library/Group Containers/group.net.whatsapp.WhatsApp.private/\n"
                f"  - {home_dir}/Library/Group Containers/group.net.whatsapp.family/\n\n"
                f"Please ensure:\n"
                f"  1. WhatsApp Desktop is installed\n"
                f"  2. WhatsApp Desktop has been opened and synced with your phone\n"
                f"  3. Messages have been downloaded from your device"
            )
            raise FileNotFoundError(error_msg)
    
    def _get_connection(self):
        """Get a read-only connection to the database."""
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
    
    def _preload_contact_names(self) -> dict:
        """Pre-load all contact names to avoid repeated database queries."""
        contact_cache = {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Load contact names from chat sessions
            cursor.execute("""
                SELECT ZCONTACTJID, ZPARTNERNAME 
                FROM ZWACHATSESSION 
                WHERE ZCONTACTJID IS NOT NULL AND ZPARTNERNAME IS NOT NULL
            """)
            
            for jid, name in cursor.fetchall():
                if jid and name:
                    contact_cache[jid] = name
        
        # Try to load from ContactsV2 database if available
        try:
            contacts_db_path = self.db_path.replace('ChatStorage.sqlite', 'ContactsV2.sqlite')
            if os.path.exists(contacts_db_path):
                contacts_conn = sqlite3.connect(f"file:{contacts_db_path}?mode=ro", uri=True)
                contacts_cursor = contacts_conn.cursor()
                
                contacts_cursor.execute("""
                    SELECT ZWHATSAPPID, ZFULLNAME 
                    FROM ZWAADDRESSBOOKCONTACT 
                    WHERE ZWHATSAPPID IS NOT NULL AND ZFULLNAME IS NOT NULL
                """)
                
                for jid, name in contacts_cursor.fetchall():
                    if jid and name:
                        contact_cache[jid] = name  # This will override chat session names with full names
                
                contacts_conn.close()
        except:
            pass
            
        return contact_cache

    def _get_contact_name_by_jid(self, jid: str, contact_cache: dict) -> str:
        """Get contact name by WhatsApp JID using pre-loaded cache."""
        if not jid:
            return jid
            
        # Check cache first
        if jid in contact_cache:
            return contact_cache[jid]
            
        # Return just the phone number part if no name found
        if '@' in jid:
            return jid.split('@')[0]
        return jid

    def _get_cache_key(self, query: str, fuzzy_threshold: int, sort_by: str) -> str:
        """Generate a cache key for search parameters."""
        return f"{query.lower()}:{fuzzy_threshold}:{sort_by}"

    def _clear_cache(self):
        """Clear the search results cache."""
        self._search_cache = {}
        self._current_cache_key = None

    def search_messages(self, query: str, limit: int = 50, fuzzy_threshold: int = 60, 
                       sort_by: str = "relevance", page: int = 1) -> dict:
        """
        Search messages using fuzzy matching with pagination.
        
        Args:
            query: Search query string
            limit: Maximum number of results per page
            fuzzy_threshold: Minimum fuzzy match score (0-100)
            sort_by: Sorting method - "relevance" or "time" 
            page: Page number (1-based)
        
        Returns:
            Dict containing:
            - results: List of tuples (message_text, sender_info, chat_name, timestamp, match_score)
            - total_matches: Total number of matching messages
            - page: Current page number
            - total_pages: Total number of pages
            - has_more: Whether there are more results
        """
        # Handle empty queries
        if not query or not query.strip():
            return {
                "results": [],
                "total_matches": 0,
                "page": page,
                "total_pages": 0,
                "has_more": False
            }
        
        # Generate cache key for this search
        cache_key = self._get_cache_key(query, fuzzy_threshold, sort_by)
        
        # Check if we have cached results for this search configuration
        if cache_key in self._search_cache:
            print("📄 Using cached search results...")
            cached_results = self._search_cache[cache_key]
            total_matches = len(cached_results)
            
            # Calculate pagination from cached results
            total_pages = (total_matches + limit - 1) // limit if total_matches > 0 else 0
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_results = cached_results[start_idx:end_idx]
            
            return {
                "results": page_results,
                "total_matches": total_matches,
                "page": page,
                "total_pages": total_pages,
                "has_more": page < total_pages
            }
        
        # If cache key changed, we're doing a new search - clear old cache
        if self._current_cache_key != cache_key:
            if self._current_cache_key:
                print("🔄 Search parameters changed, clearing cache...")
            self._current_cache_key = cache_key
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Use database filtering first to reduce memory usage
            # For typo tolerance, make the database filtering less restrictive
            query_words = query.lower().split()
            
            # Build more flexible database query for typos
            if len(query_words) == 1 and len(query.strip()) > 3:
                # For single words, use broader pattern matching to catch typos
                word = query_words[0]
                like_patterns = [
                    f"%{word}%",  # Contains the word exactly
                ]
                
                # Add patterns for common typos
                if len(word) > 4:
                    # Missing characters at different positions
                    for i in range(1, len(word)):
                        # Missing character at position i
                        typo_word = word[:i] + word[i+1:]
                        if len(typo_word) > 2:
                            like_patterns.append(f"%{typo_word}%")
                    
                    # Extra character patterns (for insertions) - use fuzzy substring matching
                    for i in range(len(word)):
                        # Split word and match parts separately
                        if i > 0 and i < len(word) - 1:
                            part1 = word[:i]
                            part2 = word[i:]
                            if len(part1) > 1 and len(part2) > 1:
                                like_patterns.append(f"%{part1}%{part2}%")
                
                # Add original patterns for basic cases
                like_patterns.extend([
                    f"%{word[:-1]}%",  # Missing last character
                    f"%{word[1:]}%",   # Missing first character
                ])
                
                where_clause = " OR ".join(["LOWER(m.ZTEXT) LIKE ?" for _ in like_patterns])
                params = like_patterns
            else:
                # For multi-word queries or short queries, use simpler matching
                where_clause = "LOWER(m.ZTEXT) LIKE ? OR LOWER(m.ZTEXT) GLOB ?"
                params = [f"%{query.lower()}%", f"*{query.lower()}*"]
            
            # Get messages that likely match using database LIKE query
            cursor.execute(f"""
                SELECT 
                    m.ZTEXT as message_text,
                    c.ZPARTNERNAME as chat_name,
                    m.ZMESSAGEDATE as timestamp,
                    m.ZISFROMME as is_from_me,
                    m.ZFROMJID as from_jid,
                    CASE 
                        WHEN m.ZGROUPMEMBER IS NOT NULL THEN gm.ZMEMBERJID
                        ELSE m.ZFROMJID
                    END as actual_sender_jid
                FROM ZWAMESSAGE m
                LEFT JOIN ZWACHATSESSION c ON m.ZCHATSESSION = c.Z_PK
                LEFT JOIN ZWAGROUPMEMBER gm ON m.ZGROUPMEMBER = gm.Z_PK
                WHERE m.ZTEXT IS NOT NULL 
                AND LENGTH(m.ZTEXT) >= 3
                AND ({where_clause})
                ORDER BY m.ZMESSAGEDATE DESC
                LIMIT 50000
            """, params)
            
            messages = cursor.fetchall()
            
        # Pre-load contact names for efficient lookup
        print("📇 Pre-loading contact names...")
        contact_cache = self._preload_contact_names()
        
        # Perform optimized fuzzy matching
        print(f"🔍 Processing {len(messages):,} candidate messages...")
        
        results = []
        processed = 0
        
        for msg_text, chat_name, timestamp, is_from_me, from_jid, actual_sender_jid in messages:
            processed += 1
            
            # Quick exact match check first (fastest)
            exact_match = query.lower() in msg_text.lower()
            if exact_match:
                score = 100
            else:
                # Only do expensive fuzzy matching if needed
                partial_score = fuzz.partial_ratio(query.lower(), msg_text.lower())
                token_score = fuzz.token_set_ratio(query.lower(), msg_text.lower())
                
                # For short queries, be more strict with partial matching
                if len(query) <= 4:
                    score = token_score
                    if score < 90:
                        continue
                else:
                    score = max(partial_score, token_score)
                    if score < 80:
                        continue
            
            if score >= fuzzy_threshold:
                # Convert timestamp (Core Data timestamp to Unix timestamp)
                unix_timestamp = timestamp + 978307200
                readable_time = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                # Determine sender with more detail (using pre-loaded cache)
                if is_from_me:
                    sender_info = "You"
                else:
                    sender_name = self._get_contact_name_by_jid(actual_sender_jid, contact_cache)
                    phone_number = actual_sender_jid.split('@')[0] if '@' in actual_sender_jid else actual_sender_jid
                    
                    if sender_name and sender_name != phone_number:
                        sender_info = f"{sender_name} ({phone_number})"
                    else:
                        sender_info = phone_number
                
                results.append((msg_text, sender_info, chat_name, readable_time, score))
                
                # Early termination optimization: if we have way more results than needed, 
                # we can stop processing (for very common terms)
                if len(results) > 10000:  # Much more than any reasonable pagination
                    print(f"⚡ Found {len(results):,} results, stopping early for performance")
                    break
        
        print(f"✅ Found {len(results):,} matching messages from {processed:,} candidates")
        
        # Sort results based on sort_by parameter
        if sort_by == "time":
            # Sort by timestamp (most recent first), then by score
            results.sort(key=lambda x: (x[3], x[4]), reverse=True)
        else:  # sort_by == "relevance" (default)
            # Sort by match score (highest first), then by timestamp
            results.sort(key=lambda x: (x[4], x[3]), reverse=True)
        
        # Cache the complete sorted results for this search configuration
        self._search_cache[cache_key] = results
        print(f"💾 Cached {len(results):,} results for future page navigation")
        
        # Calculate pagination
        total_matches = len(results)
        total_pages = (total_matches + limit - 1) // limit  # Ceiling division
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        page_results = results[start_idx:end_idx]
        
        return {
            "results": page_results,
            "total_matches": total_matches,
            "page": page,
            "total_pages": total_pages,
            "has_more": page < total_pages
        }
    
    def view_chat(self, contact_query: str, limit: int = 50, page: int = 1) -> dict:
        """
        View entire chat conversation with a specific contact.
        
        Args:
            contact_query: Contact name to find
            limit: Maximum number of messages per page
            page: Page number (1-based)
        
        Returns:
            Dict containing:
            - results: List of tuples (message_text, sender_info, timestamp, is_from_user)
            - total_matches: Total number of messages in the conversation
            - page: Current page number
            - total_pages: Total number of pages
            - has_more: Whether there are more results
            - contact_name: The actual contact name found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # First find the best matching contact
            cursor.execute("""
                SELECT Z_PK, ZPARTNERNAME, ZCONTACTJID
                FROM ZWACHATSESSION 
                WHERE ZPARTNERNAME IS NOT NULL
            """)
            
            contacts = cursor.fetchall()
            
            # Find best matching contact with improved matching
            contact_matches = []
            
            for pk, name, jid in contacts:
                if name:
                    # Use multiple matching strategies for better accuracy
                    partial_score = fuzz.partial_ratio(contact_query.lower(), name.lower())
                    token_score = fuzz.token_set_ratio(contact_query.lower(), name.lower())
                    ratio_score = fuzz.ratio(contact_query.lower(), name.lower())
                    
                    # Check for exact substring match (highest priority)
                    exact_match = contact_query.lower() in name.lower()
                    
                    # Check if query matches the start of the name (higher priority)
                    starts_with_match = name.lower().startswith(contact_query.lower())
                    
                    # Check for word-level matching with better scoring
                    query_words = contact_query.lower().split()
                    name_words = name.lower().split()
                    
                    # Count exact word matches and partial word matches
                    exact_word_matches = 0
                    partial_word_matches = 0
                    total_important_words = 0
                    
                    for q_word in query_words:
                        if len(q_word) > 2:
                            total_important_words += 1
                            if q_word in name_words:
                                exact_word_matches += 1
                            else:
                                # Check for partial matches (substring in any name word)
                                if any(q_word in n_word or n_word in q_word for n_word in name_words if len(n_word) > 2):
                                    partial_word_matches += 1
                    
                    # Calculate combined match score
                    if total_important_words > 0:
                        exact_word_ratio = exact_word_matches / total_important_words
                        partial_word_ratio = partial_word_matches / total_important_words
                        word_match_score = exact_word_ratio + (partial_word_ratio * 0.7)  # Partial matches worth 70%
                    else:
                        word_match_score = 0
                    
                    # Calculate combined score with bonuses for different match types
                    if starts_with_match:
                        combined_score = 105  # Highest priority for names that start with query
                    elif exact_match:
                        combined_score = 100  # High priority for exact substring matches
                    elif word_match_score >= 0.5:  # At least half the important words match (counting partial)
                        # Give higher score for higher word match ratio
                        combined_score = 90 + (word_match_score * 5)  # 90-95 range
                    else:
                        combined_score = max(partial_score, token_score, ratio_score)
                    
                    if combined_score > 60:
                        has_good_match = starts_with_match or exact_match or word_match_score >= 0.5
                        contact_matches.append((pk, name, jid, combined_score, has_good_match))
            
            if not contact_matches:
                return {
                    "results": [],
                    "total_matches": 0,
                    "page": page,
                    "total_pages": 0,
                    "has_more": False,
                    "contact_name": None
                }
            
            # Sort by exact match first, then by score
            contact_matches.sort(key=lambda x: (x[4], x[3]), reverse=True)
            
            # Show matching contacts if there are multiple good matches
            if len(contact_matches) > 1:
                print(f"🔍 Found {len(contact_matches)} matching contacts:")
                for i, (_, name, _, score, exact) in enumerate(contact_matches[:5]):  # Show top 5
                    prefix = "🎯" if exact else "📊"
                    print(f"  {i+1}. {prefix} {name} ({score}%)")
                print(f"📝 Selected: {contact_matches[0][1]}")
                print()
            
            pk, contact_name, jid, _, _ = contact_matches[0]
            
            # Get total message count for this chat
            cursor.execute("""
                SELECT COUNT(*)
                FROM ZWAMESSAGE 
                WHERE ZCHATSESSION = ? AND ZTEXT IS NOT NULL
            """, (pk,))
            
            total_messages = cursor.fetchone()[0]
            
            if total_messages == 0:
                return {
                    "results": [],
                    "total_matches": 0,
                    "page": page,
                    "total_pages": 0,
                    "has_more": False,
                    "contact_name": contact_name
                }
            
            # Calculate pagination
            total_pages = (total_messages + limit - 1) // limit
            offset = (page - 1) * limit
            
            # Get messages for this page (most recent page first, but chronological within page)
            # First get all messages in descending order to calculate correct offset for recent pages
            cursor.execute("""
                SELECT ZTEXT, ZMESSAGEDATE, ZISFROMME
                FROM ZWAMESSAGE 
                WHERE ZCHATSESSION = ? AND ZTEXT IS NOT NULL
                ORDER BY ZMESSAGEDATE DESC
                LIMIT ? OFFSET ?
            """, (pk, limit, offset))
            
            messages = cursor.fetchall()
            
            # Reverse the messages so they appear in chronological order within the page
            # (oldest message at top, newest at bottom)
            messages = messages[::-1]
            
            # Format results
            results = []
            for msg_text, timestamp, is_from_me in messages:
                # Convert timestamp
                unix_timestamp = timestamp + 978307200
                readable_time = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                
                sender = "You" if is_from_me else contact_name
                
                results.append((msg_text, sender, readable_time, is_from_me))
            
            return {
                "results": results,
                "total_matches": total_messages,
                "page": page,
                "total_pages": total_pages,
                "has_more": page < total_pages,
                "contact_name": contact_name
            }

    def search_by_contact(self, contact_query: str, message_query: str = "", limit: int = 50, page: int = 1) -> dict:
        """
        Search messages from specific contacts with pagination.
        
        Args:
            contact_query: Contact name to search for
            message_query: Optional message content filter
            limit: Maximum number of results per page
            page: Page number (1-based)
        
        Returns:
            Dict containing:
            - results: List of tuples (message_text, sender_info, timestamp, match_score)
            - total_matches: Total number of matching messages
            - page: Current page number
            - total_pages: Total number of pages
            - has_more: Whether there are more results
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # First find matching contacts
            cursor.execute("""
                SELECT Z_PK, ZPARTNERNAME, ZCONTACTJID
                FROM ZWACHATSESSION 
                WHERE ZPARTNERNAME IS NOT NULL
            """)
            
            contacts = cursor.fetchall()
            
            # Find best matching contacts
            contact_matches = []
            for pk, name, jid in contacts:
                if name:
                    score = fuzz.partial_ratio(contact_query.lower(), name.lower())
                    if score > 60:
                        contact_matches.append((pk, name, jid, score))
            
            if not contact_matches:
                return {
                    "results": [],
                    "total_matches": 0,
                    "page": page,
                    "total_pages": 0,
                    "has_more": False
                }
            
            # Sort by match score and get top matches
            contact_matches.sort(key=lambda x: x[3], reverse=True)
            best_matches = contact_matches[:5]  # Top 5 contact matches
            
            results = []
            for pk, contact_name, jid, contact_score in best_matches:
                # Get messages from this contact
                if message_query:
                    cursor.execute("""
                        SELECT ZTEXT, ZMESSAGEDATE, ZISFROMME
                        FROM ZWAMESSAGE 
                        WHERE ZCHATSESSION = ? AND ZTEXT IS NOT NULL
                        ORDER BY ZMESSAGEDATE DESC
                        LIMIT 1000
                    """, (pk,))
                else:
                    cursor.execute("""
                        SELECT ZTEXT, ZMESSAGEDATE, ZISFROMME
                        FROM ZWAMESSAGE 
                        WHERE ZCHATSESSION = ? AND ZTEXT IS NOT NULL
                        ORDER BY ZMESSAGEDATE DESC
                        LIMIT 100
                    """, (pk,))
                
                messages = cursor.fetchall()
                
                for msg_text, timestamp, is_from_me in messages:
                    if message_query:
                        # Skip very short messages that might create false matches
                        if len(msg_text.strip()) < 3:
                            continue
                            
                        # Use improved matching logic
                        partial_score = fuzz.partial_ratio(message_query.lower(), msg_text.lower())
                        token_score = fuzz.token_set_ratio(message_query.lower(), msg_text.lower())
                        
                        # Check for exact substring match first
                        exact_match = message_query.lower() in msg_text.lower()
                        
                        # For short queries, be more strict with partial matching
                        if len(message_query) <= 4:
                            msg_score = token_score
                            # For very short queries, require very high similarity or exact match
                            if msg_score < 90 and not exact_match:
                                continue
                        else:
                            # For longer queries, prioritize exact matches or high similarity
                            if exact_match:
                                msg_score = 100
                            else:
                                msg_score = max(partial_score, token_score)
                                # Require higher threshold for non-exact matches
                                if msg_score < 80:
                                    continue
                        combined_score = contact_score + msg_score
                        display_score = msg_score  # Show message match score
                    else:
                        msg_score = 0
                        combined_score = contact_score
                        display_score = contact_score  # Show contact match score
                    
                    # Convert timestamp
                    unix_timestamp = timestamp + 978307200
                    readable_time = datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')
                    
                    sender = "You" if is_from_me else contact_name
                    
                    results.append((msg_text, sender, readable_time, display_score, combined_score))
            
            # Sort by combined score
            results.sort(key=lambda x: x[4], reverse=True)
            
            # Remove combined_score for display and calculate pagination
            display_results = [(msg, sender, time, score) for msg, sender, time, score, _ in results]
            total_matches = len(display_results)
            
            if total_matches == 0:
                return {
                    "results": [],
                    "total_matches": 0,
                    "page": page,
                    "total_pages": 0,
                    "has_more": False
                }
            
            # Calculate pagination
            total_pages = (total_matches + limit - 1) // limit  # Ceiling division
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_results = display_results[start_idx:end_idx]
            
            return {
                "results": page_results,
                "total_matches": total_matches,
                "page": page,
                "total_pages": total_pages,
                "has_more": page < total_pages
            }
    
    def get_chat_statistics(self) -> dict:
        """Get basic statistics about the chat database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM ZWAMESSAGE")
            stats['total_messages'] = cursor.fetchone()[0]
            
            # Messages with text
            cursor.execute("SELECT COUNT(*) FROM ZWAMESSAGE WHERE ZTEXT IS NOT NULL AND LENGTH(ZTEXT) > 0")
            stats['text_messages'] = cursor.fetchone()[0]
            
            # Total chats
            cursor.execute("SELECT COUNT(*) FROM ZWACHATSESSION")
            stats['total_chats'] = cursor.fetchone()[0]
            
            # Active chats (with names)
            cursor.execute("SELECT COUNT(*) FROM ZWACHATSESSION WHERE ZPARTNERNAME IS NOT NULL")
            stats['named_chats'] = cursor.fetchone()[0]
            
            return stats

def display_results(results, start_index=1):
    """Display search results with improved formatting and clear separators"""
    if not results:
        return
    
    for i, result in enumerate(results, start_index):
        text, sender_info, chat_name, timestamp, score = result
        
        # Message separator with number
        print(f"{'─' * 60}")
        print(f"📧 Message {i}")
        print(f"{'─' * 60}")
        
        # Sender and timestamp info
        print(f"👤 From: {sender_info}")
        print(f"🕒 Time: {timestamp}")
        
        # Chat info (if different from sender)
        if chat_name and chat_name != sender_info:
            print(f"💬 Chat: {chat_name}")
        
        # Match score with visual indicator
        score_emoji = "🎯" if score == 100 else "📊"
        print(f"{score_emoji} Score: {score}%")
        
        # Message content with better formatting
        print(f"💭 Message:")
        
        # Handle long messages with proper wrapping
        if len(text) > 200:
            # Show first 200 characters, then indicate truncation
            preview_text = text[:200].strip()
            print(f"   {preview_text}...")
            print(f"   📏 [{len(text)} characters total - showing first 200]")
        else:
            # For shorter messages, show full content with indentation
            print(f"   {text}")
        
        print()  # Empty line after each message

def display_chat_messages(results, start_index=1):
    """Display chat messages in conversation format"""
    if not results:
        return
    
    for i, result in enumerate(results, start_index):
        text, sender_info, timestamp, is_from_me = result
        
        # Message separator with number
        print(f"{'─' * 60}")
        print(f"💬 Message {i}")
        print(f"{'─' * 60}")
        
        # Sender and timestamp info with different styling for user vs contact
        if is_from_me:
            print(f"👤 You")
        else:
            print(f"👥 {sender_info}")
        
        print(f"🕒 Time: {timestamp}")
        
        # Message content with better formatting
        print(f"💭 Message:")
        
        # Handle long messages with proper wrapping
        if len(text) > 200:
            # Show first 200 characters, then indicate truncation
            preview_text = text[:200].strip()
            print(f"   {preview_text}...")
            print(f"   📏 [{len(text)} characters total - showing first 200]")
        else:
            # For shorter messages, show full content with indentation
            print(f"   {text}")
        
        print()  # Empty line after each message

def interactive_chat_viewing(searcher, contact_query, limit):
    """Interactive mode for viewing entire chat conversations"""
    current_page = 1
    
    while True:
        # Get chat messages for current page
        chat_result = searcher.view_chat(contact_query, limit, current_page)
        
        if chat_result["total_matches"] == 0:
            print(f"No chat found or no messages with contact: {contact_query}")
            return
        
        # Display chat header
        print("\n" + "="*60)
        print(f"💬 Conversation with {chat_result['contact_name']}")
        print(f"Total messages: {chat_result['total_matches']:,}")
        print(f"Page {chat_result['page']} of {chat_result['total_pages']}")
        print("="*60 + "\n")
        
        # Display messages
        display_chat_messages(chat_result["results"])
        
        # Show navigation options
        print("="*60)
        options = []
        if current_page > 1:
            options.append("p) Previous page")
        if chat_result["has_more"]:
            options.append("n) Next page")
        
        options.extend([
            "g) Go to specific page",
            "l) Change page size",
            "q) Quit"
        ])
        
        print("Options: " + " | ".join(options))
        
        # Get user input
        try:
            choice = input("\nChoose an option: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'n' and chat_result["has_more"]:
                current_page += 1
            elif choice == 'p' and current_page > 1:
                current_page -= 1
            elif choice == 'g':
                try:
                    page_num = int(input(f"Enter page number (1-{chat_result['total_pages']}): "))
                    if 1 <= page_num <= chat_result['total_pages']:
                        current_page = page_num
                    else:
                        print(f"Invalid page number. Must be between 1 and {chat_result['total_pages']}")
                        input("Press Enter to continue...")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    input("Press Enter to continue...")
            elif choice == 'l':
                try:
                    new_limit = int(input("Enter new page size (1-100): "))
                    if 1 <= new_limit <= 100:
                        limit = new_limit
                        current_page = 1  # Reset to first page
                    else:
                        print("Invalid page size. Must be between 1 and 100")
                        input("Press Enter to continue...")
                except ValueError:
                    print("Invalid input. Please enter a number.")
                    input("Press Enter to continue...")
            else:
                print("Invalid option. Please try again.")
                input("Press Enter to continue...")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except EOFError:
            print("\n\nExiting...")
            break

def interactive_pagination(searcher, query, limit, threshold, sort_by, contact=None):
    """Interactive pagination mode for browsing results"""
    current_page = 1
    current_sort = sort_by
    
    # Show cache status
    cache_key = searcher._get_cache_key(query, threshold, sort_by)
    if cache_key in searcher._search_cache:
        print(f"📄 Found cached results for this search")
    
    while True:
        # Get results for current page
        if contact:
            # Contact search now supports pagination
            search_result = searcher.search_by_contact(contact, query, limit, current_page)
            
            if search_result["total_matches"] == 0:
                print(f"No messages found matching '{query}' from {contact}")
                return
            
            # Clear screen for better UX (optional)
            print("\n" + "="*60)
            print(f"Found {search_result['total_matches']:,} matching messages from {contact}")
            print(f"Page {search_result['page']} of {search_result['total_pages']}")
            print("="*60 + "\n")
            
            # Convert contact search results to the same format as regular search results
            formatted_results = []
            for result in search_result["results"]:
                text, sender, timestamp, score = result
                # Format: (message_text, sender_info, chat_name, timestamp, score)
                formatted_results.append((text, sender, contact, timestamp, score))
            
            display_results(formatted_results)
            
            # Show navigation options
            print("="*60)
            options = []
            if current_page > 1:
                options.append("p) Previous page")
            if search_result["has_more"]:
                options.append("n) Next page")
            
            options.extend([
                "g) Go to specific page",
                "l) Change page size",
                "q) Quit"
            ])
            
            print("Options: " + " | ".join(options))
            
            # Get user input for contact search
            try:
                choice = input("\nChoose an option: ").strip().lower()
                
                if choice == 'q':
                    break
                elif choice == 'n' and search_result["has_more"]:
                    current_page += 1
                elif choice == 'p' and current_page > 1:
                    current_page -= 1
                elif choice == 'g':
                    try:
                        page_num = int(input(f"Enter page number (1-{search_result['total_pages']}): "))
                        if 1 <= page_num <= search_result['total_pages']:
                            current_page = page_num
                        else:
                            print(f"Invalid page number. Must be between 1 and {search_result['total_pages']}")
                            input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        input("Press Enter to continue...")
                elif choice == 'l':
                    try:
                        new_limit = int(input("Enter new page size (1-100): "))
                        if 1 <= new_limit <= 100:
                            limit = new_limit
                            current_page = 1  # Reset to first page
                        else:
                            print("Invalid page size. Must be between 1 and 100")
                            input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        input("Press Enter to continue...")
                else:
                    print("Invalid option. Please try again.")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                print("\n\nExiting...")
                break
        else:
            search_result = searcher.search_messages(query, limit, threshold, current_sort, current_page)
            
            if search_result["total_matches"] == 0:
                print(f"No messages found matching '{query}'")
                return
            
            # Clear screen for better UX (optional)
            print("\n" + "="*60)
            print(f"Found {search_result['total_matches']:,} matching messages")
            print(f"Page {search_result['page']} of {search_result['total_pages']} (sorted by {current_sort})")
            print("="*60 + "\n")
            
            # Display results
            display_results(search_result["results"])
            
            # Show navigation options
            print("="*60)
            options = []
            if current_page > 1:
                options.append("p) Previous page")
            if search_result["has_more"]:
                options.append("n) Next page")
            
            if current_sort == "relevance":
                options.append("t) Sort by time")
            else:
                options.append("r) Sort by relevance")
            
            options.extend([
                "g) Go to specific page",
                "l) Change page size",
                "c) Clear cache (force refresh)",
                "q) Quit"
            ])
            
            print("Options: " + " | ".join(options))
            
            # Get user input
            try:
                choice = input("\nChoose an option: ").strip().lower()
                
                if choice == 'q':
                    break
                elif choice == 'n' and search_result["has_more"]:
                    current_page += 1
                elif choice == 'p' and current_page > 1:
                    current_page -= 1
                elif choice == 't' and current_sort == "relevance":
                    current_sort = "time"
                    current_page = 1  # Reset to first page when changing sort
                elif choice == 'r' and current_sort == "time":
                    current_sort = "relevance" 
                    current_page = 1  # Reset to first page when changing sort
                elif choice == 'g':
                    try:
                        page_num = int(input(f"Enter page number (1-{search_result['total_pages']}): "))
                        if 1 <= page_num <= search_result['total_pages']:
                            current_page = page_num
                        else:
                            print(f"Invalid page number. Must be between 1 and {search_result['total_pages']}")
                            input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        input("Press Enter to continue...")
                elif choice == 'l':
                    try:
                        new_limit = int(input("Enter new page size (1-100): "))
                        if 1 <= new_limit <= 100:
                            limit = new_limit
                            current_page = 1  # Reset to first page
                        else:
                            print("Invalid page size. Must be between 1 and 100")
                            input("Press Enter to continue...")
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                        input("Press Enter to continue...")
                elif choice == 'c':
                    # Clear cache and force refresh
                    print("🗑️ Clearing search cache...")
                    searcher._clear_cache()
                    print("Cache cleared. Next search will refresh from database.")
                    input("Press Enter to continue...")
                else:
                    print("Invalid option. Please try again.")
                    input("Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except EOFError:
                print("\n\nExiting...")
                break

def main():
    parser = argparse.ArgumentParser(description='Browse WhatsApp conversations and search messages')
    parser.add_argument('chat', nargs='?', help='Contact name to view conversation with')
    parser.add_argument('-q', '--query', help='Search for specific messages (requires chat contact or use alone for global search)')
    parser.add_argument('-l', '--limit', type=int, default=20, help='Maximum number of results per page (default: 20)')
    parser.add_argument('-t', '--threshold', type=int, default=60, help='Fuzzy match threshold 0-100 (default: 60)')
    parser.add_argument('-c', '--contact', help='Search within specific contact (alternative to positional chat argument)')
    parser.add_argument('-p', '--page', type=int, default=1, help='Page number (default: 1)')
    parser.add_argument('-s', '--sort', choices=['relevance', 'time'], default='relevance', 
                       help='Sort by relevance or time (default: relevance)')
    parser.add_argument('--no-interactive', action='store_true', 
                       help='Disable interactive mode (use traditional command-line pagination)')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    
    args = parser.parse_args()
    
    try:
        searcher = WhatsAppSearcher()
        
        if args.stats:
            stats = searcher.get_chat_statistics()
            print("WhatsApp Database Statistics:")
            print(f"  Total messages: {stats['total_messages']:,}")
            print(f"  Text messages: {stats['text_messages']:,}")
            print(f"  Total chats: {stats['total_chats']:,}")
            print(f"  Named chats: {stats['named_chats']:,}")
            return
        
        # Determine the operation mode based on arguments
        contact_name = args.chat or args.contact  # Positional chat or --contact option
        
        if contact_name:
            # Chat viewing or contact-specific search mode
            if args.query:
                # Search within specific contact
                if not args.no_interactive:
                    interactive_pagination(searcher, args.query, args.limit, args.threshold, args.sort, contact_name)
                else:
                    # Non-interactive contact search
                    contact_result = searcher.search_by_contact(contact_name, args.query, args.limit, args.page)
                    
                    if contact_result["total_matches"] == 0:
                        print(f"No messages found matching '{args.query}' from {contact_name}")
                        return
                    
                    # Display pagination info
                    print(f"Found {contact_result['total_matches']:,} matching messages from {contact_name}")
                    print(f"Page {contact_result['page']} of {contact_result['total_pages']}")
                    print()
                    
                    # Convert contact search results to display format
                    formatted_results = []
                    for result in contact_result["results"]:
                        text, sender, timestamp, score = result
                        formatted_results.append((text, sender, contact_name, timestamp, score))
                    
                    display_results(formatted_results)
                    
                    # Show pagination hints
                    if contact_result["has_more"]:
                        next_page = contact_result["page"] + 1
                        print(f"💡 To see more results, use: --page {next_page}")
                        print(f"💡 For interactive navigation, remove --no-interactive flag")
            else:
                # Chat viewing mode (no query, just browse conversation)
                if not args.no_interactive:
                    # Interactive chat viewing
                    interactive_chat_viewing(searcher, contact_name, args.limit)
                else:
                    # Non-interactive chat viewing
                    chat_result = searcher.view_chat(contact_name, args.limit, args.page)
                    
                    if chat_result["total_matches"] == 0:
                        print(f"No chat found or no messages with contact: {contact_name}")
                        return
                    
                    print(f"Viewing conversation with {chat_result['contact_name']}")
                    print(f"Total messages: {chat_result['total_matches']:,}")
                    print(f"Page {chat_result['page']} of {chat_result['total_pages']}")
                    print()
                    
                    display_chat_messages(chat_result["results"])
                    
                    # Show pagination hints
                    if chat_result["has_more"]:
                        next_page = chat_result["page"] + 1
                        print(f"💡 To see more messages, use: --page {next_page}")
                        print(f"💡 For interactive navigation, remove --no-interactive flag")
            return
        
        # Global search mode (no contact specified)
        if not args.query:
            print("Error: Either provide a contact name to view conversation, or use --query for global search")
            parser.print_help()
            return
        
        # Global search mode - search all messages
        if not args.no_interactive:
            interactive_pagination(searcher, args.query, args.limit, args.threshold, args.sort, None)
            return
        
        # Non-interactive global search
        search_result = searcher.search_messages(args.query, args.limit, args.threshold, args.sort, args.page)
        
        if search_result["total_matches"] == 0:
            print(f"No messages found matching '{args.query}'")
            return
        
        # Display pagination info
        print(f"Found {search_result['total_matches']:,} matching messages")
        print(f"Page {search_result['page']} of {search_result['total_pages']} (sorted by {args.sort})")
        print()
        
        results = search_result["results"]
        
        # Display results (paginated search format)
        display_results(results)
        
        # Show pagination hints
        if search_result["has_more"]:
            next_page = search_result["page"] + 1
            print(f"💡 To see more results, use: --page {next_page}")
            if args.sort == "relevance":
                print(f"💡 To sort by time instead, use: --sort time")
            else:
                print(f"💡 To sort by relevance instead, use: --sort relevance")
            print(f"💡 For interactive navigation, remove --no-interactive flag")
            
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()