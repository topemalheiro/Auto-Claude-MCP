"""
Comprehensive Tests for context.keyword_extractor module
========================================================

Tests for KeywordExtractor class including edge cases,
special characters, empty inputs, and all functionality paths.
"""

import pytest

from context.keyword_extractor import KeywordExtractor


class TestExtractKeywordsBasic:
    """Tests for basic keyword extraction"""

    def test_extract_keywords_basic(self):
        """Test basic keyword extraction"""
        task = "Add user authentication with JWT tokens"
        result = KeywordExtractor.extract_keywords(task)
        assert isinstance(result, list)
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result
        assert "tokens" in result

    def test_extract_keywords_default_max(self):
        """Test default max_keywords parameter"""
        task = " ".join([f"keyword{i}" for i in range(20)])
        result = KeywordExtractor.extract_keywords(task)
        assert len(result) <= 10

    def test_extract_keywords_custom_max(self):
        """Test custom max_keywords parameter"""
        task = " ".join([f"keyword{i}" for i in range(20)])
        result = KeywordExtractor.extract_keywords(task, max_keywords=5)
        assert len(result) <= 5

    def test_extract_keywords_empty_string(self):
        """Test with empty string"""
        result = KeywordExtractor.extract_keywords("")
        assert result == []

    def test_extract_keywords_whitespace_only(self):
        """Test with whitespace only"""
        result = KeywordExtractor.extract_keywords("   \n\t  ")
        assert result == []


class TestStopwordFiltering:
    """Tests for stopword filtering"""

    def test_common_stopwords_filtered(self):
        """Test that common stopwords are filtered"""
        task = "the user authentication to the system with the new feature"
        result = KeywordExtractor.extract_keywords(task)
        assert "the" not in result
        assert "to" not in result
        assert "with" not in result
        assert "new" not in result  # "new" is in stopwords

    def test_all_stopwords(self):
        """Test task with only stopwords"""
        task = "the a an to for of in on at by with and or but"
        result = KeywordExtractor.extract_keywords(task)
        # Should filter short words too
        assert len(result) == 0

    def test_action_verbs_filtered(self):
        """Test that action verbs are filtered"""
        task = "add create implement build fix update change modify the user authentication"
        result = KeywordExtractor.extract_keywords(task)
        # Action verbs should be filtered
        assert "add" not in result
        assert "create" not in result
        assert "implement" not in result
        # But content words should remain
        assert "user" in result
        assert "authentication" in result

    def test_auxiliary_verbs_filtered(self):
        """Test that auxiliary verbs are filtered"""
        task = "is are was were be been being have has had do does did will would could should may might must can"
        result = KeywordExtractor.extract_keywords(task)
        # All should be filtered as stopwords or too short
        for word in ["is", "are", "was", "were", "be", "been", "being"]:
            assert word not in result

    def test_pronouns_filtered(self):
        """Test that pronouns are filtered"""
        task = "i you we they it this that these those"
        result = KeywordExtractor.extract_keywords(task)
        # All are too short (< 3 chars)
        assert len(result) == 0


class TestLengthFiltering:
    """Tests for minimum length filtering"""

    def test_short_words_filtered(self):
        """Test that words shorter than 3 chars are filtered"""
        task = "api endpoint user id db js py ts"
        result = KeywordExtractor.extract_keywords(task)
        # Short words should be filtered
        assert "id" not in result
        assert "db" not in result
        assert "js" not in result
        assert "py" not in result
        assert "ts" not in result
        # But longer words should remain
        assert "api" in result
        assert "endpoint" in result
        assert "user" in result

    def test_exactly_three_chars(self):
        """Test that 3-char words are included"""
        task = "api use get set put"
        result = KeywordExtractor.extract_keywords(task)
        assert "api" in result
        assert "use" in result
        assert "get" in result


class TestTokenization:
    """Tests for word tokenization"""

    def test_word_boundaries(self):
        """Test correct word boundary detection"""
        task = "user_name user-name username"
        result = KeywordExtractor.extract_keywords(task)
        # Regex captures alphanumeric + underscore
        # Hyphens are NOT captured - they split words
        assert "user_name" in result
        # "user-name" would be tokenized as "user" and "name"
        assert "username" in result

    def test_underscore_identifiers(self):
        """Test underscore-separated identifiers"""
        task = "add user_authentication with jwt_token validation"
        result = KeywordExtractor.extract_keywords(task)
        # Underscore words are treated as single tokens
        assert "user_authentication" in result
        assert "jwt_token" in result

    def test_camel_case_preserved(self):
        """Test that camelCase is preserved"""
        task = "implement AuthenticationHandler for UserService"
        result = KeywordExtractor.extract_keywords(task)
        # CamelCase is treated as single word
        assert "AuthenticationHandler" in result or "authenticationhandler" in result

    def test_numbers_in_words(self):
        """Test words with numbers"""
        task = "implement api v2 endpoints for user123"
        result = KeywordExtractor.extract_keywords(task)
        # Should include alphanumeric words
        assert any("api" in kw for kw in result)
        assert any("endpoints" in kw or "endpoint" in kw for kw in result)


class TestCaseHandling:
    """Tests for case handling"""

    def test_lowercase_output(self):
        """Test that output is always lowercase"""
        task = "Implement USER Authentication with JWT TOKENS"
        result = KeywordExtractor.extract_keywords(task)
        # All output should be lowercase
        assert all(kw == kw.lower() for kw in result)

    def test_case_insensitive_stopword_filtering(self):
        """Test that stopwords are filtered regardless of case"""
        task = "The User THE user THE user"
        result = KeywordExtractor.extract_keywords(task)
        # "the" should be filtered in all cases
        assert "the" not in result
        assert "user" in result


class TestDeduplication:
    """Tests for keyword deduplication"""

    def test_duplicate_removal(self):
        """Test that duplicate keywords are removed"""
        task = "user user user authentication authentication"
        result = KeywordExtractor.extract_keywords(task)
        # Should have only unique keywords
        assert result.count("user") == 1
        assert result.count("authentication") == 1

    def test_case_insensitive_dedup(self):
        """Test deduplication is case-insensitive"""
        task = "user USER User AuThEnTiCaTe authentication"
        result = KeywordExtractor.extract_keywords(task)
        # Should deduplicate across case variations
        assert result.count("user") == 1
        assert result.count("authentication") == 1

    def test_order_preservation(self):
        """Test that order is preserved after deduplication"""
        task = "zebra apple zebra banana apple"
        result = KeywordExtractor.extract_keywords(task)
        # First occurrence should determine order
        zebra_idx = result.index("zebra")
        apple_idx = result.index("apple")
        banana_idx = result.index("banana")
        assert zebra_idx < apple_idx < banana_idx


class TestSpecialCharacters:
    """Tests for special character handling"""

    def test_punctuation_removed(self):
        """Test that punctuation is removed from tokens"""
        task = "user, authentication; jwt: tokens. endpoint!"
        result = KeywordExtractor.extract_keywords(task)
        # Should extract words without punctuation
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result
        assert "tokens" in result
        assert "endpoint" in result

    def test_special_characters_only(self):
        """Test task with only special characters"""
        task = "@#$%^&*()_+-=[]{}|;:,.<>?"
        result = KeywordExtractor.extract_keywords(task)
        # Might extract underscore as a token
        assert isinstance(result, list)

    def test_mixed_alphanumeric(self):
        """Test alphanumeric with special chars"""
        task = "add api/v2 endpoint with user_id validation"
        result = KeywordExtractor.extract_keywords(task)
        # Should extract meaningful words
        assert "endpoint" in result
        assert "validation" in result


class TestEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_single_word(self):
        """Test with single word"""
        result = KeywordExtractor.extract_keywords("authentication")
        assert result == ["authentication"]

    def test_single_word_stopword(self):
        """Test with single stopword"""
        result = KeywordExtractor.extract_keywords("the")
        assert result == []

    def test_single_word_short(self):
        """Test with single short word"""
        result = KeywordExtractor.extract_keywords("id")
        assert result == []

    def test_very_long_word(self):
        """Test with very long word"""
        long_word = "a" * 1000
        result = KeywordExtractor.extract_keywords(f"implement {long_word} feature")
        assert long_word in result

    def test_unicode_characters(self):
        """Test with unicode characters"""
        task = "implement user authentication with caf"
        result = KeywordExtractor.extract_keywords(task)
        # Should handle unicode gracefully
        assert isinstance(result, list)

    def test_multiple_spaces(self):
        """Test with multiple consecutive spaces"""
        task = "user    authentication     jwt"
        result = KeywordExtractor.extract_keywords(task)
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result

    def test_newlines_and_tabs(self):
        """Test with newlines and tabs"""
        task = "user\nauthentication\tjwt\n\ttokens"
        result = KeywordExtractor.extract_keywords(task)
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result
        assert "tokens" in result

    def test_leading_trailing_whitespace(self):
        """Test with leading and trailing whitespace"""
        task = "   user authentication jwt   "
        result = KeywordExtractor.extract_keywords(task)
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result

    def test_technical_terms(self):
        """Test extraction of technical terms"""
        task = "add REST API endpoint with JSON response and SQL query"
        result = KeywordExtractor.extract_keywords(task)
        # Technical terms should be extracted
        assert "rest" in result
        assert "api" in result
        assert "endpoint" in result
        assert "json" in result
        assert "response" in result
        assert "sql" in result
        assert "query" in result

    def test_code_related_terms(self):
        """Test extraction of code-related terms"""
        task = "implement class UserService method authenticate_user"
        result = KeywordExtractor.extract_keywords(task)
        # Code-related terms should be extracted
        assert "class" in result
        assert "userservice" in result or "UserService" in result.lower()
        assert "method" in result
        assert "authenticate_user" in result or "authenticateuser" in result

    def test_url_and_email(self):
        """Test with URLs and email addresses"""
        task = "add user authentication at api.example.com contact admin@example.com"
        result = KeywordExtractor.extract_keywords(task)
        # Should extract meaningful words from URLs/emails
        assert "user" in result
        assert "authentication" in result

    def test_hashtags_and_mentions(self):
        """Test with hashtags and mentions"""
        task = "add #authentication feature for @user service"
        result = KeywordExtractor.extract_keywords(task)
        # Should extract words without symbols
        assert "authentication" in result
        assert "user" in result

    def test_mixed_language_terms(self):
        """Test with mixed language technical terms"""
        task = "add GraphQL endpoint with database schema"
        result = KeywordExtractor.extract_keywords(task)
        # Should extract technical terms
        assert "graphql" in result or "graph" in result
        assert "endpoint" in result
        assert "database" in result
        assert "schema" in result


class TestRealWorldExamples:
    """Tests with real-world task descriptions"""

    def test_authentication_task(self):
        """Test realistic authentication task description"""
        task = "Add user authentication with JWT tokens to the API endpoint"
        result = KeywordExtractor.extract_keywords(task)
        assert "user" in result
        assert "authentication" in result
        assert "jwt" in result
        assert "tokens" in result
        assert "api" in result
        assert "endpoint" in result

    def test_database_task(self):
        """Test realistic database task description"""
        task = "Implement database migration for user profiles with new fields"
        result = KeywordExtractor.extract_keywords(task)
        assert "database" in result
        assert "migration" in result
        assert "user" in result
        assert "profiles" in result
        assert "fields" in result

    def test_frontend_task(self):
        """Test realistic frontend task description"""
        task = "Create new user profile page component with form validation"
        result = KeywordExtractor.extract_keywords(task)
        assert "user" in result
        assert "profile" in result
        assert "page" in result
        assert "component" in result
        assert "form" in result
        assert "validation" in result

    def test_bug_fix_task(self):
        """Test realistic bug fix task description"""
        task = "Fix authentication bug where user login fails with invalid credentials"
        result = KeywordExtractor.extract_keywords(task)
        assert "authentication" in result
        assert "bug" in result
        assert "user" in result
        assert "login" in result
        assert "fails" in result
        assert "invalid" in result
        assert "credentials" in result
