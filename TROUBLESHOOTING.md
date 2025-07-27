# Troubleshooting Guide
## WhatsApp Companion Data Analyzer

### Common Issues

#### "No WhatsApp database found" Error

**Symptoms:**
- Error message: "No WhatsApp database found"
- Application exits immediately after startup

**Causes and Solutions:**

1. **WhatsApp Desktop not installed**
   - **Solution**: Install WhatsApp Desktop from the Mac App Store
   - **Verification**: Check if WhatsApp.app exists in `/Applications/`

2. **WhatsApp Desktop never used**
   - **Solution**: Open WhatsApp Desktop and complete initial setup
   - **Verification**: Ensure messages have synced from your phone

3. **Group Containers directory missing**
   - **Solution**: Check if directory exists: `/Users/[username]/Library/Group Containers/`
   - **Alternative**: Try running WhatsApp Desktop once to create necessary directories

4. **Messages not synced from iPhone**
   - **Solution**: Open WhatsApp on iPhone → Settings → Linked Devices → Manage → Sync messages
   - **Wait time**: Allow 5-10 minutes for large message histories

5. **Different user account**
   - **Problem**: The tool looks for databases in the current user's directory
   - **Solution**: The tool now automatically detects the current user's home directory, so this should work for any user

#### Search Returns No Results

**Symptoms:**
- "No messages found matching 'query'"
- Empty result set for queries that should match

**Troubleshooting Steps:**

1. **Lower fuzzy threshold**
   ```bash
   # Try with more lenient matching
   python3 whatsapp_search.py --query "your_query" --threshold 50
   ```

2. **Check database statistics**
   ```bash
   # Verify database has messages
   python3 whatsapp_search.py --stats
   ```

3. **Try exact substring search**
   ```bash
   # Use shorter, more specific terms
   python3 whatsapp_search.py --query "pizza" --threshold 100
   ```

4. **Verify message content**
   - Check if messages actually contain the search terms
   - Consider alternative spellings or terms

#### Contact Not Found

**Symptoms:**
- "No chat found or no messages with contact: [name]"
- Wrong contact selected by fuzzy matching

**Solutions:**

1. **Try different name variations**
   ```bash
   # Try partial names
   python3 whatsapp_search.py "John"
   python3 whatsapp_search.py "Doe"
   python3 whatsapp_search.py "John D"
   ```

2. **Use phone numbers**
   ```bash
   # If name matching fails, try phone number
   python3 whatsapp_search.py "1234567890"
   ```

3. **Check contact list**
   ```bash
   # View all contacts to find correct name
   python3 whatsapp_search.py --stats  # Shows named chats count
   ```

#### Performance Issues

**Symptoms:**
- Searches take longer than 5 seconds
- High memory usage
- System becomes unresponsive

**Performance Solutions:**

1. **Reduce search scope**
   ```bash
   # Use higher threshold to reduce candidates
   python3 whatsapp_search.py --query "term" --threshold 80
   
   # Limit results per page
   python3 whatsapp_search.py --query "term" --limit 10
   ```

2. **Clear cache if memory issues**
   ```bash
   # In interactive mode, press 'c' to clear cache
   # Or restart the application
   ```

3. **Use more specific queries**
   ```bash
   # Longer, more specific terms perform better
   python3 whatsapp_search.py --query "specific project meeting"
   ```

#### Interactive Mode Issues

**Symptoms:**
- Keys not responding in interactive mode
- Application hangs on input
- Unexpected exits

**Solutions:**

1. **Terminal compatibility**
   - Use Terminal.app or iTerm2
   - Avoid SSH sessions or remote terminals
   - Ensure terminal supports UTF-8

2. **Use non-interactive mode**
   ```bash
   # Fallback to traditional pagination
   python3 whatsapp_search.py --query "term" --no-interactive
   ```

3. **Check keyboard input**
   - Press Enter after single-key commands if needed
   - Use lowercase letters (n, p, q, etc.)

#### Database Access Issues

**Symptoms:**
- "Cannot access WhatsApp database" error
- Permission denied errors
- SQLite errors

**Solutions:**

1. **Check file permissions**
   ```bash
   # Verify database files are readable
   ls -la ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/
   ```

2. **Close WhatsApp Desktop**
   - Quit WhatsApp Desktop application
   - Database may be locked during active use

3. **Restart and retry**
   - Close all WhatsApp applications
   - Wait 30 seconds and retry

### System Requirements Issues

#### Python Version Compatibility

**Minimum Requirements:**
- Python 3.6+
- sqlite3 module (included in Python standard library)

**Check your Python version:**
```bash
python3 --version
python3 -c "import sqlite3; print('SQLite3 available')"
```

#### Missing Dependencies

**Install all required packages:**
```bash
pip3 install -r requirements.txt
```

**Individual package issues:**
```bash
# If fuzzywuzzy installation fails
pip3 install fuzzywuzzy

# For better performance (optional but recommended)
pip3 install python-Levenshtein

# For running tests
pip3 install pytest
```

#### macOS Version Compatibility

**Supported versions:**
- macOS 10.14 (Mojave) and later
- Requires WhatsApp Desktop compatibility

**Potential issues:**
- Older macOS versions may have different database paths
- Security restrictions may block database access

### Debug Information

#### Enable Verbose Output

The tool includes built-in progress indicators:
- Database path discovery messages
- Contact pre-loading status
- Search progress counters
- Cache status indicators

#### Manual Database Verification

**Check database paths manually:**
```bash
# Verify database exists and is readable
ls -la ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite

# Check database isn't corrupted
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite ".schema" | head
```

**Verify database contents:**
```bash
# Check if database has messages
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite "SELECT COUNT(*) FROM ZWAMESSAGE;"

# Check if database has contacts
sqlite3 ~/Library/Group\ Containers/group.net.whatsapp.WhatsApp.shared/ChatStorage.sqlite "SELECT COUNT(*) FROM ZWACHATSESSION WHERE ZPARTNERNAME IS NOT NULL;"
```

### Getting Help

#### Log Collection

If issues persist, collect this information:
1. **System info**: `system_profiler SPSoftwareDataType | grep "System Version"`
2. **Python version**: `python3 --version`
3. **Database status**: `python3 whatsapp_search.py --stats`
4. **Error messages**: Full error output
5. **WhatsApp version**: Check WhatsApp Desktop version in App Store

#### Reporting Issues

When reporting issues, include:
- macOS version
- Python version
- Complete error message
- Steps to reproduce
- Expected vs actual behavior
- Database statistics output (if accessible)

### Advanced Troubleshooting

#### Custom Database Paths

If databases are in non-standard locations:

1. **Edit `whatsapp_search.py`**
2. **Modify the `get_whatsapp_db_paths()` function** (around line 18)
3. **Add your custom paths to the returned list**

```python
def get_whatsapp_db_paths():
    """Get WhatsApp database paths for the current user."""
    home_dir = os.path.expanduser("~")
    base_path = os.path.join(home_dir, "Library", "Group Containers")
    
    paths = [
        os.path.join(base_path, "group.net.whatsapp.WhatsApp.shared", "ChatStorage.sqlite"),
        os.path.join(base_path, "group.net.whatsapp.WhatsApp.private", "ChatStorage.sqlite"),
        os.path.join(base_path, "group.net.whatsapp.family", "ChatStorage.sqlite")
    ]
    
    # Add custom paths if needed
    # paths.append("/path/to/your/custom/ChatStorage.sqlite")
    
    return paths
```

#### Multiple WhatsApp Accounts

For users with multiple WhatsApp Business or personal accounts:
- Each account may use different Group Container paths
- Check all Group Container directories
- Add additional paths to `WHATSAPP_DB_PATHS`

#### Performance Tuning

For very large databases (>100,000 messages):

1. **Increase search thresholds**
2. **Use more specific queries**
3. **Consider running during off-peak hours**
4. **Monitor system memory during searches**

### Still Having Issues?

If none of these solutions work:
1. **Check GitHub Issues**: Look for similar problems
2. **Create New Issue**: Include all debug information
3. **Try Safe Mode**: Use `--no-interactive` mode as fallback
4. **Test with Statistics**: Verify `--stats` command works first