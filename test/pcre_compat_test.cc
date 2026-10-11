//
// term-ime: every runtime regex entry point must behave like upstream's
// boost::regex (PCRE) as far as std::regex (ECMAScript) allows.
//
// Before this translation was shared, only the algebra rules went through it:
// recognizer patterns, encoder exclude_patterns, translator/patterns and
// speller auto_select_pattern compiled the raw schema string. A PCRE-only
// pattern either stopped matching silently or -- where the caller had no
// try/catch, as encoder/translator/speller had none -- threw std::regex_error
// out of a Load* call and killed the engine. These tests pin both halves:
// \l/\u are translated, and an untranslatable pattern degrades to "not
// loaded" with the surrounding load still succeeding.
//
#include <gtest/gtest.h>
#include <regex>
// common.h first: encoder.h uses its string/vector aliases without including
// it.
#include <rime/common.h>
#include <rime/config.h>
#include <rime/algo/encoder.h>
#include <rime/gear/recognizer.h>
#include <rime/gear/translator_commons.h>
#include <rime/pcre_translator.hpp>

using namespace rime;  // NOLINT(build/namespaces)

TEST(RimePcreCompatTest, ShorthandClassesAreRewritten) {
  EXPECT_EQ("^([a-z]+)\\d$", TranslatePcreClasses("^(\\l+)\\d$"));
  EXPECT_EQ("[A-Z]", TranslatePcreClasses("\\u"));
  EXPECT_EQ("[a-zA-Z]", TranslatePcreClasses("[\\l\\u]"));
  // Inside a character class the range has to stay bare: "[a" + "a-z" + "]"
  // unions 'a' with a-z, whereas rewriting \l to [a-z] there would nest
  // ("[[a-z]]") and change what matches.
  EXPECT_EQ("^[aa-z]$", TranslatePcreClasses("^[a\\l]$"));
}

TEST(RimePcreCompatTest, EscapedBackslashStaysLiteral) {
  // "\\l" is an escaped backslash followed by 'l'; translating it would
  // corrupt a pattern that legitimately wants a literal backslash.
  EXPECT_EQ("^a\\\\l$", TranslatePcreClasses("^a\\\\l$"));
}

TEST(RimePcreCompatTest, ClassesBothDialectsShareAreLeftAlone) {
  EXPECT_EQ("^\\d\\w\\s\\D\\W\\S$",
            TranslatePcreClasses("^\\d\\w\\s\\D\\W\\S$"));
}

TEST(RimePcreCompatTest, UntranslatableConstructsAreLeftToFailLoudly) {
  // ECMAScript has no lookbehind and no Unicode property classes; rewriting
  // them into something that matches differently would be worse than the
  // regex_error, so they pass through untouched.
  EXPECT_EQ("(?<=a)b", TranslatePcreClasses("(?<=a)b"));
  EXPECT_EQ("\\p{Han}+", TranslatePcreClasses("\\p{Han}+"));
  EXPECT_THROW(std::regex(TranslatePcreClasses("(?<=a)b")), std::regex_error);
}

TEST(RimePcreCompatTest, RecognizerPatternsGoThroughTranslation) {
  Config config;
  config["recognizer"]["patterns"]["letters"] = "^\\l+$";
  config["recognizer"]["patterns"]["untranslatable"] = "(?<![A-Z]):[^;]*;?$";
  RecognizerPatterns patterns;
  patterns.LoadConfig(&config, "recognizer");
  // The good one loads and means "one or more lowercase letters" -- under the
  // untranslated ECMAScript reading it would only match runs of 'l'.
  ASSERT_EQ(1, patterns.size());
  auto it = patterns.find("letters");
  ASSERT_NE(it, patterns.end());
  EXPECT_TRUE(std::regex_search("abc", it->second));
  EXPECT_TRUE(std::regex_search("lll", it->second));
  EXPECT_FALSE(std::regex_search("ABC", it->second));
  // The lookbehind one is skipped, not thrown: the schema still loads.
  EXPECT_EQ(patterns.end(), patterns.find("untranslatable"));
}

TEST(RimePcreCompatTest,
     EncoderExcludePatternsAreTranslatedAndTolerateBadOnes) {
  Config config;
  config["encoder"]["rules"][0]["formula"] = "AaAzBaBz";
  config["encoder"]["rules"][0]["length_equal"] = 2;
  config["encoder"]["exclude_patterns"][0] = "^\\l+$";
  TableEncoder encoder;
  encoder.LoadSettings(&config);
  ASSERT_TRUE(encoder.loaded());
  EXPECT_TRUE(encoder.IsCodeExcluded("ab"));
  EXPECT_FALSE(encoder.IsCodeExcluded("AB"));

  // An untranslatable exclude pattern used to throw std::regex_error out of
  // LoadSettings; now it is skipped and the encoder still loads.
  Config bad;
  bad["encoder"]["rules"][0]["formula"] = "AaAzBaBz";
  bad["encoder"]["rules"][0]["length_equal"] = 2;
  bad["encoder"]["exclude_patterns"][0] = "(?<=a)\\l";
  TableEncoder bad_encoder;
  EXPECT_NO_THROW(bad_encoder.LoadSettings(&bad));
  EXPECT_TRUE(bad_encoder.loaded());
  EXPECT_FALSE(bad_encoder.IsCodeExcluded("aab"));
}

TEST(RimePcreCompatTest, TranslatorPatternsSkipUntranslatableEntries) {
  Config config;
  config["translator"]["patterns"][0] = "^\\l+$";
  config["translator"]["patterns"][1] = "\\p{Han}";
  auto list = config.GetList("translator/patterns");
  ASSERT_TRUE(bool(list));
  Patterns patterns;
  EXPECT_TRUE(patterns.Load(list));
  ASSERT_EQ(1, patterns.size());
  EXPECT_TRUE(std::regex_search("abc", patterns.front()));
  EXPECT_FALSE(std::regex_search("ABC", patterns.front()));
}