"""
Tests for project.command_registry.languages
============================================

Comprehensive tests for the language commands module including:
- LANGUAGE_COMMANDS dictionary validation
- Language-specific command sets
- Data structure integrity
- Coverage across programming languages
"""

import pytest

from project.command_registry.languages import LANGUAGE_COMMANDS


# =============================================================================
# LANGUAGE_COMMANDS Structure Tests
# =============================================================================

class TestLanguageCommandsStructure:
    """Tests for LANGUAGE_COMMANDS dictionary structure."""

    def test_language_commands_is_dict(self):
        """Test that LANGUAGE_COMMANDS is a dictionary."""
        assert isinstance(LANGUAGE_COMMANDS, dict)

    def test_language_commands_not_empty(self):
        """Test that LANGUAGE_COMMANDS is not empty."""
        assert len(LANGUAGE_COMMANDS) > 0

    def test_language_commands_all_keys_strings(self):
        """Test that all LANGUAGE_COMMANDS keys are strings."""
        assert all(isinstance(key, str) for key in LANGUAGE_COMMANDS.keys())

    def test_language_commands_all_values_sets(self):
        """Test that all LANGUAGE_COMMANDS values are sets."""
        assert all(isinstance(value, set) for value in LANGUAGE_COMMANDS.values())

    def test_language_commands_all_values_string_sets(self):
        """Test that all values contain only strings."""
        for cmd_set in LANGUAGE_COMMANDS.values():
            assert all(isinstance(cmd, str) for cmd in cmd_set)

    def test_language_commands_no_empty_keys(self):
        """Test that LANGUAGE_COMMANDS has no empty keys."""
        assert "" not in LANGUAGE_COMMANDS

    def test_language_commands_no_empty_values(self):
        """Test that no language has empty command set."""
        assert all(len(cmds) > 0 for cmds in LANGUAGE_COMMANDS.values())


# =============================================================================
# Python Language Tests
# =============================================================================

class TestPythonLanguageCommands:
    """Tests for Python language commands."""

    def test_python_key_exists(self):
        """Test that 'python' key exists."""
        assert "python" in LANGUAGE_COMMANDS

    def test_python_has_python_command(self):
        """Test that Python has 'python' command."""
        assert "python" in LANGUAGE_COMMANDS["python"]

    def test_python_has_python3(self):
        """Test that Python has 'python3' command."""
        assert "python3" in LANGUAGE_COMMANDS["python"]

    def test_python_has_pip(self):
        """Test that Python has pip commands."""
        assert "pip" in LANGUAGE_COMMANDS["python"]
        assert "pip3" in LANGUAGE_COMMANDS["python"]

    def test_python_has_pipx(self):
        """Test that Python has pipx command."""
        assert "pipx" in LANGUAGE_COMMANDS["python"]

    def test_python_has_ipython(self):
        """Test that Python has ipython."""
        assert "ipython" in LANGUAGE_COMMANDS["python"]

    def test_python_has_jupyter(self):
        """Test that Python has jupyter commands."""
        assert "jupyter" in LANGUAGE_COMMANDS["python"]
        assert "notebook" in LANGUAGE_COMMANDS["python"]

    def test_python_has_debuggers(self):
        """Test that Python has debugger commands."""
        assert "pdb" in LANGUAGE_COMMANDS["python"]
        assert "pudb" in LANGUAGE_COMMANDS["python"]


# =============================================================================
# JavaScript/TypeScript Language Tests
# =============================================================================

class TestJavaScriptLanguageCommands:
    """Tests for JavaScript language commands."""

    def test_javascript_key_exists(self):
        """Test that 'javascript' key exists."""
        assert "javascript" in LANGUAGE_COMMANDS

    def test_javascript_has_node(self):
        """Test that JavaScript has node command."""
        assert "node" in LANGUAGE_COMMANDS["javascript"]

    def test_javascript_has_npm(self):
        """Test that JavaScript has npm command."""
        assert "npm" in LANGUAGE_COMMANDS["javascript"]

    def test_javascript_has_npx(self):
        """Test that JavaScript has npx command."""
        assert "npx" in LANGUAGE_COMMANDS["javascript"]


class TestTypeScriptLanguageCommands:
    """Tests for TypeScript language commands."""

    def test_typescript_key_exists(self):
        """Test that 'typescript' key exists."""
        assert "typescript" in LANGUAGE_COMMANDS

    def test_typescript_has_tsc(self):
        """Test that TypeScript has tsc command."""
        assert "tsc" in LANGUAGE_COMMANDS["typescript"]

    def test_typescript_has_ts_node(self):
        """Test that TypeScript has ts-node command."""
        assert "ts-node" in LANGUAGE_COMMANDS["typescript"]

    def test_typescript_has_tsx(self):
        """Test that TypeScript has tsx command."""
        assert "tsx" in LANGUAGE_COMMANDS["typescript"]


# =============================================================================
# Rust Language Tests
# =============================================================================

class TestRustLanguageCommands:
    """Tests for Rust language commands."""

    def test_rust_key_exists(self):
        """Test that 'rust' key exists."""
        assert "rust" in LANGUAGE_COMMANDS

    def test_rust_has_cargo(self):
        """Test that Rust has cargo command."""
        assert "cargo" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_rustc(self):
        """Test that Rust has rustc command."""
        assert "rustc" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_rustup(self):
        """Test that Rust has rustup command."""
        assert "rustup" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_rustfmt(self):
        """Test that Rust has rustfmt command."""
        assert "rustfmt" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_rust_analyzer(self):
        """Test that Rust has rust-analyzer command."""
        assert "rust-analyzer" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_cargo_subcommands(self):
        """Test that Rust has cargo subcommand binaries."""
        assert "cargo-clippy" in LANGUAGE_COMMANDS["rust"]
        assert "cargo-fmt" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_cargo_watch(self):
        """Test that Rust has cargo-watch."""
        assert "cargo-watch" in LANGUAGE_COMMANDS["rust"]

    def test_rust_has_wasm_tools(self):
        """Test that Rust has WASM-related tools."""
        assert "wasm-pack" in LANGUAGE_COMMANDS["rust"]
        assert "wasm-bindgen" in LANGUAGE_COMMANDS["rust"]


# =============================================================================
# Go Language Tests
# =============================================================================

class TestGoLanguageCommands:
    """Tests for Go language commands."""

    def test_go_key_exists(self):
        """Test that 'go' key exists."""
        assert "go" in LANGUAGE_COMMANDS

    def test_go_has_go_command(self):
        """Test that Go has go command."""
        assert "go" in LANGUAGE_COMMANDS["go"]

    def test_go_has_gofmt(self):
        """Test that Go has gofmt command."""
        assert "gofmt" in LANGUAGE_COMMANDS["go"]

    def test_go_has_tooling(self):
        """Test that Go has tooling commands."""
        assert "golint" in LANGUAGE_COMMANDS["go"]
        assert "gopls" in LANGUAGE_COMMANDS["go"]


# =============================================================================
# Ruby Language Tests
# =============================================================================

class TestRubyLanguageCommands:
    """Tests for Ruby language commands."""

    def test_ruby_key_exists(self):
        """Test that 'ruby' key exists."""
        assert "ruby" in LANGUAGE_COMMANDS

    def test_ruby_has_ruby_command(self):
        """Test that Ruby has ruby command."""
        assert "ruby" in LANGUAGE_COMMANDS["ruby"]

    def test_ruby_has_gem(self):
        """Test that Ruby has gem command."""
        assert "gem" in LANGUAGE_COMMANDS["ruby"]

    def test_ruby_has_irb(self):
        """Test that Ruby has irb command."""
        assert "irb" in LANGUAGE_COMMANDS["ruby"]


# =============================================================================
# PHP Language Tests
# =============================================================================

class TestPHPLanguageCommands:
    """Tests for PHP language commands."""

    def test_php_key_exists(self):
        """Test that 'php' key exists."""
        assert "php" in LANGUAGE_COMMANDS

    def test_php_has_php_command(self):
        """Test that PHP has php command."""
        assert "php" in LANGUAGE_COMMANDS["php"]

    def test_php_has_composer(self):
        """Test that PHP has composer command."""
        assert "composer" in LANGUAGE_COMMANDS["php"]


# =============================================================================
# Java/JVM Languages Tests
# =============================================================================

class TestJavaLanguageCommands:
    """Tests for Java language commands."""

    def test_java_key_exists(self):
        """Test that 'java' key exists."""
        assert "java" in LANGUAGE_COMMANDS

    def test_java_has_java_command(self):
        """Test that Java has java command."""
        assert "java" in LANGUAGE_COMMANDS["java"]

    def test_java_has_javac(self):
        """Test that Java has javac command."""
        assert "javac" in LANGUAGE_COMMANDS["java"]

    def test_java_has_jar(self):
        """Test that Java has jar command."""
        assert "jar" in LANGUAGE_COMMANDS["java"]

    def test_java_has_maven(self):
        """Test that Java has maven commands."""
        assert "mvn" in LANGUAGE_COMMANDS["java"]
        assert "maven" in LANGUAGE_COMMANDS["java"]

    def test_java_has_gradle(self):
        """Test that Java has gradle commands."""
        assert "gradle" in LANGUAGE_COMMANDS["java"]
        assert "gradlew" in LANGUAGE_COMMANDS["java"]


class TestKotlinLanguageCommands:
    """Tests for Kotlin language commands."""

    def test_kotlin_key_exists(self):
        """Test that 'kotlin' key exists."""
        assert "kotlin" in LANGUAGE_COMMANDS

    def test_kotlin_has_kotlin_command(self):
        """Test that Kotlin has kotlin command."""
        assert "kotlin" in LANGUAGE_COMMANDS["kotlin"]

    def test_kotlin_has_kotlinc(self):
        """Test that Kotlin has kotlinc command."""
        assert "kotlinc" in LANGUAGE_COMMANDS["kotlin"]


class TestScalaLanguageCommands:
    """Tests for Scala language commands."""

    def test_scala_key_exists(self):
        """Test that 'scala' key exists."""
        assert "scala" in LANGUAGE_COMMANDS

    def test_scala_has_scala_command(self):
        """Test that Scala has scala command."""
        assert "scala" in LANGUAGE_COMMANDS["scala"]

    def test_scala_has_scalac(self):
        """Test that Scala has scalac command."""
        assert "scalac" in LANGUAGE_COMMANDS["scala"]

    def test_scala_has_sbt(self):
        """Test that Scala has sbt command."""
        assert "sbt" in LANGUAGE_COMMANDS["scala"]


# =============================================================================
# C# Language Tests
# =============================================================================

class TestCSharpLanguageCommands:
    """Tests for C# language commands."""

    def test_csharp_key_exists(self):
        """Test that 'csharp' key exists."""
        assert "csharp" in LANGUAGE_COMMANDS

    def test_csharp_has_dotnet(self):
        """Test that C# has dotnet command."""
        assert "dotnet" in LANGUAGE_COMMANDS["csharp"]

    def test_csharp_has_nuget(self):
        """Test that C# has nuget command."""
        assert "nuget" in LANGUAGE_COMMANDS["csharp"]

    def test_csharp_has_msbuild(self):
        """Test that C# has msbuild command."""
        assert "msbuild" in LANGUAGE_COMMANDS["csharp"]


# =============================================================================
# C/C++ Language Tests
# =============================================================================

class TestCLanguageCommands:
    """Tests for C language commands."""

    def test_c_key_exists(self):
        """Test that 'c' key exists."""
        assert "c" in LANGUAGE_COMMANDS

    def test_c_has_gcc(self):
        """Test that C has gcc command."""
        assert "gcc" in LANGUAGE_COMMANDS["c"]

    def test_c_has_clang(self):
        """Test that C has clang command."""
        assert "clang" in LANGUAGE_COMMANDS["c"]

    def test_c_has_make(self):
        """Test that C has make command."""
        assert "make" in LANGUAGE_COMMANDS["c"]

    def test_c_has_cmake(self):
        """Test that C has cmake command."""
        assert "cmake" in LANGUAGE_COMMANDS["c"]

    def test_c_has_build_tools(self):
        """Test that C has build tools."""
        assert "ar" in LANGUAGE_COMMANDS["c"]
        assert "nm" in LANGUAGE_COMMANDS["c"]
        assert "strip" in LANGUAGE_COMMANDS["c"]


class TestCppLanguageCommands:
    """Tests for C++ language commands."""

    def test_cpp_key_exists(self):
        """Test that 'cpp' key exists."""
        assert "cpp" in LANGUAGE_COMMANDS

    def test_cpp_has_gpp(self):
        """Test that C++ has g++ command."""
        assert "g++" in LANGUAGE_COMMANDS["cpp"]

    def test_cpp_has_clangpp(self):
        """Test that C++ has clang++ command."""
        assert "clang++" in LANGUAGE_COMMANDS["cpp"]

    def test_cpp_shares_with_c(self):
        """Test that C++ shares most commands with C."""
        c_commands = LANGUAGE_COMMANDS["c"]
        cpp_commands = LANGUAGE_COMMANDS["cpp"]
        # Most should overlap
        overlap = c_commands.intersection(cpp_commands)
        assert len(overlap) > len(c_commands) * 0.8


# =============================================================================
# Elixir Language Tests
# =============================================================================

class TestElixirLanguageCommands:
    """Tests for Elixir language commands."""

    def test_elixir_key_exists(self):
        """Test that 'elixir' key exists."""
        assert "elixir" in LANGUAGE_COMMANDS

    def test_elixir_has_elixir_command(self):
        """Test that Elixir has elixir command."""
        assert "elixir" in LANGUAGE_COMMANDS["elixir"]

    def test_elixir_has_mix(self):
        """Test that Elixir has mix command."""
        assert "mix" in LANGUAGE_COMMANDS["elixir"]

    def test_elixir_has_iex(self):
        """Test that Elixir has iex command."""
        assert "iex" in LANGUAGE_COMMANDS["elixir"]


# =============================================================================
# Haskell Language Tests
# =============================================================================

class TestHaskellLanguageCommands:
    """Tests for Haskell language commands."""

    def test_haskell_key_exists(self):
        """Test that 'haskell' key exists."""
        assert "haskell" in LANGUAGE_COMMANDS

    def test_haskell_has_ghc(self):
        """Test that Haskell has ghc command."""
        assert "ghc" in LANGUAGE_COMMANDS["haskell"]

    def test_haskell_has_ghci(self):
        """Test that Haskell has ghci command."""
        assert "ghci" in LANGUAGE_COMMANDS["haskell"]

    def test_haskell_has_cabal(self):
        """Test that Haskell has cabal command."""
        assert "cabal" in LANGUAGE_COMMANDS["haskell"]

    def test_haskell_has_stack(self):
        """Test that Haskell has stack command."""
        assert "stack" in LANGUAGE_COMMANDS["haskell"]


# =============================================================================
# Lua Language Tests
# =============================================================================

class TestLuaLanguageCommands:
    """Tests for Lua language commands."""

    def test_lua_key_exists(self):
        """Test that 'lua' key exists."""
        assert "lua" in LANGUAGE_COMMANDS

    def test_lua_has_lua_command(self):
        """Test that Lua has lua command."""
        assert "lua" in LANGUAGE_COMMANDS["lua"]

    def test_lua_has_luarocks(self):
        """Test that Lua has luarocks command."""
        assert "luarocks" in LANGUAGE_COMMANDS["lua"]


# =============================================================================
# Perl Language Tests
# =============================================================================

class TestPerlLanguageCommands:
    """Tests for Perl language commands."""

    def test_perl_key_exists(self):
        """Test that 'perl' key exists."""
        assert "perl" in LANGUAGE_COMMANDS

    def test_perl_has_perl_command(self):
        """Test that Perl has perl command."""
        assert "perl" in LANGUAGE_COMMANDS["perl"]

    def test_perl_has_cpan(self):
        """Test that Perl has cpan command."""
        assert "cpan" in LANGUAGE_COMMANDS["perl"]

    def test_perl_has_cpanm(self):
        """Test that Perl has cpanm command."""
        assert "cpanm" in LANGUAGE_COMMANDS["perl"]


# =============================================================================
# Swift Language Tests
# =============================================================================

class TestSwiftLanguageCommands:
    """Tests for Swift language commands."""

    def test_swift_key_exists(self):
        """Test that 'swift' key exists."""
        assert "swift" in LANGUAGE_COMMANDS

    def test_swift_has_swift_command(self):
        """Test that Swift has swift command."""
        assert "swift" in LANGUAGE_COMMANDS["swift"]

    def test_swift_has_swiftc(self):
        """Test that Swift has swiftc command."""
        assert "swiftc" in LANGUAGE_COMMANDS["swift"]

    def test_swift_has_xcodebuild(self):
        """Test that Swift has xcodebuild command."""
        assert "xcodebuild" in LANGUAGE_COMMANDS["swift"]


# =============================================================================
# Zig Language Tests
# =============================================================================

class TestZigLanguageCommands:
    """Tests for Zig language commands."""

    def test_zig_key_exists(self):
        """Test that 'zig' key exists."""
        assert "zig" in LANGUAGE_COMMANDS

    def test_zig_has_zig_command(self):
        """Test that Zig has zig command."""
        assert "zig" in LANGUAGE_COMMANDS["zig"]


# =============================================================================
# Dart/Flutter Language Tests
# =============================================================================

class TestDartLanguageCommands:
    """Tests for Dart language commands."""

    def test_dart_key_exists(self):
        """Test that 'dart' key exists."""
        assert "dart" in LANGUAGE_COMMANDS

    def test_dart_has_dart_command(self):
        """Test that Dart has dart command."""
        assert "dart" in LANGUAGE_COMMANDS["dart"]

    def test_dart_has_pub(self):
        """Test that Dart has pub command."""
        assert "pub" in LANGUAGE_COMMANDS["dart"]

    def test_dart_has_flutter(self):
        """Test that Dart has flutter command."""
        assert "flutter" in LANGUAGE_COMMANDS["dart"]

    def test_dart_has_legacy_tools(self):
        """Test that Dart has legacy tool commands."""
        assert "dart2js" in LANGUAGE_COMMANDS["dart"]
        assert "dartanalyzer" in LANGUAGE_COMMANDS["dart"]


# =============================================================================
# Data Integrity Tests
# =============================================================================

class TestDataIntegrity:
    """Tests for data integrity."""

    def test_no_empty_command_names(self):
        """Test no empty command names in any language."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            assert "" not in commands
            assert not any(cmd.strip() == "" for cmd in commands)

    def test_no_duplicates_within_languages(self):
        """Test no duplicate commands within a language."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            # Sets don't have duplicates, but verify
            assert len(commands) == len(set(commands))

    def test_all_commands_lowercase(self):
        """Test that all commands are lowercase (with hyphens allowed)."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            for cmd in commands:
                # Allow hyphens, but otherwise should be lowercase
                cmd_without_hyphens = cmd.replace("-", "").replace(".", "")
                assert cmd_without_hyphens.islower() or cmd_without_hyphens.isdigit()

    def test_commands_no_leading_trailing_whitespace(self):
        """Test no commands have leading/trailing whitespace."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            for cmd in commands:
                assert cmd == cmd.strip()

    def test_language_keys_lowercase(self):
        """Test that all language keys are lowercase."""
        for lang in LANGUAGE_COMMANDS.keys():
            assert lang.islower() or lang.replace("_", "").replace("+", "").islower()


# =============================================================================
# Language Coverage Tests
# =============================================================================

class TestLanguageCoverage:
    """Tests for language coverage."""

    def test_major_languages_covered(self):
        """Test that major programming languages are covered."""
        major_languages = {
            "python", "javascript", "typescript", "rust", "go",
            "ruby", "php", "java", "c", "cpp"
        }
        assert major_languages.issubset(LANGUAGE_COMMANDS.keys())

    def test_modern_languages_covered(self):
        """Test that modern languages are covered."""
        modern_languages = {"rust", "go", "dart", "zig"}
        assert modern_languages.issubset(LANGUAGE_COMMANDS.keys())

    def test_functional_languages_covered(self):
        """Test that functional languages are covered."""
        functional_languages = {"elixir", "haskell", "scala"}
        assert functional_languages.issubset(LANGUAGE_COMMANDS.keys())

    def test_scripting_languages_covered(self):
        """Test that scripting languages are covered."""
        scripting_languages = {"python", "ruby", "php", "perl", "lua"}
        assert scripting_languages.issubset(LANGUAGE_COMMANDS.keys())

    def test_system_languages_covered(self):
        """Test that system languages are covered."""
        system_languages = {"c", "cpp", "rust", "go"}
        assert system_languages.issubset(LANGUAGE_COMMANDS.keys())


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases."""

    def test_commands_with_hyphens(self):
        """Test handling of commands with hyphens."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            hyphen_cmds = [cmd for cmd in commands if "-" in cmd]
            # Verify hyphenated commands are valid
            for cmd in hyphen_cmds:
                parts = cmd.split("-")
                assert all(part.isalnum() or part.isdigit() for part in parts)

    def test_commands_with_numbers(self):
        """Test handling of commands with numbers."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            numeric_cmds = [cmd for cmd in commands if any(c.isdigit() for c in cmd)]
            # Just verify they exist
            assert isinstance(numeric_cmds, list)

    def test_single_command_languages(self):
        """Test languages with minimal commands (if any)."""
        for lang, commands in LANGUAGE_COMMANDS.items():
            # Even minimal languages should have at least the language command
            assert len(commands) >= 1

    def test_c_cpp_overlap(self):
        """Test that C and C++ share most commands."""
        c_commands = LANGUAGE_COMMANDS.get("c", set())
        cpp_commands = LANGUAGE_COMMANDS.get("cpp", set())

        if c_commands and cpp_commands:
            overlap = c_commands.intersection(cpp_commands)
            # Should have significant overlap
            assert len(overlap) > 0
