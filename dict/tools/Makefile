# Dictionary generation tools. Everything is invoked explicitly and never wired
# into CMake -- wiring it in would bind "generate the dictionary" and
# "configure the engine" back into one build graph, while librime at runtime
# only reads the data in dict/.
#
#   make toolchain        build opencc's generators (host Python + host opencc_dict)
#   make essay            regenerate essay.txt
#   make dict             regenerate luna_pinyin.dict.yaml
#   make ocd2             regenerate the opencc binary phrase tables
#   make all              the three products above
#   make test-opencc      regenerate the opencc fixture rime_test converts against
#   make check            regenerate, then compare byte-for-byte with what dict/ commits
#   make smoke            real-engine smoke test: deploy dict/ and assert candidates
#   make audit            dead single-character readings that hijack initial-only input (read-only)
#   make audit-words      word rows with only an archaic reading, untypeable in modern pinyin (read-only)
#   make audit-coverage   composition blind spots from missing standard readings (read-only)
#   make package          build the release tarball
#
# check is the acceptance gate for every committed generated file, product data
# and the test fixture alike: a non-empty diff means a script is wrong, and the
# fix is never to edit the data to "align" it.
# smoke is the acceptance gate for usability: check can be all green while the
# engine still cannot read these files (toneless syllables, a schema pattern
# that fails to compile, entries the table builder rejects) -- only a real
# deployment proves otherwise.
# audit is the calibration reader. It needs a development-time oracle
# (pip install pypinyin); it writes no data, and what it prints, once checked
# by hand, becomes del/add lines in pinyin_fixes.txt.

TOOLS := $(CURDIR)
DICT  := $(abspath $(TOOLS)/..)
TEST  := $(abspath $(TOOLS)/../../test)
BUILD := $(TOOLS)/.build
OUT   ?= $(BUILD)/out
PKG   := $(BUILD)/pkg

OPENCC_SRC   := $(abspath $(DICT)/../deps/opencc)
OPENCC_BUILD := $(BUILD)/opencc
OPENCC_CLI   := $(OPENCC_BUILD)/src/tools/opencc
OPENCC_DICT  := $(OPENCC_BUILD)/src/tools/opencc_dict

export OPENCC_CLI
export OPENCC_BUILD
export OPENCC_SRC
export OPENCC_CONFIG_DIR := $(OPENCC_SRC)/data/config

PY ?= python3
VERSION := $(shell cat $(DICT)/VERSION)
NAME := term-ime-dict-$(VERSION)

.PHONY: all audit audit-words audit-coverage check clean dict essay ocd2 package smoke test-opencc toolchain

all: $(OUT)/essay.txt $(OUT)/luna_pinyin.dict.yaml $(OUT)/opencc

# The generator toolchain is the one place a host Python and a host-executed
# opencc_dict are allowed: it builds opencc WITH its data step.
toolchain: $(OPENCC_DICT)

$(OPENCC_DICT) $(OPENCC_CLI):
	cmake -S $(OPENCC_SRC) -B $(OPENCC_BUILD) \
	  -DCMAKE_BUILD_TYPE=Release \
	  -DBUILD_SHARED_LIBS=OFF \
	  -DBUILD_TESTING=OFF -DENABLE_GTEST=OFF \
	  -DUSE_SYSTEM_MARISA=OFF \
	  -DOPENCC_BUILD_DATA=ON -DOPENCC_BUILD_TOOLS=ON
	cmake --build $(OPENCC_BUILD)

essay: $(OUT)/essay.txt
dict: $(OUT)/luna_pinyin.dict.yaml
ocd2: $(OUT)/opencc
test-opencc: $(OUT)/test-opencc

$(OUT)/essay.txt: upgrade_essay.py protected_chars.txt t2s_char.json sources.lock | $(OUT) toolchain
	$(PY) upgrade_essay.py --out $@

$(OUT)/luna_pinyin.dict.yaml: convert_dict.py pinyin_fixes.txt protected_chars.txt t2s_char.json sources.lock | $(OUT) toolchain
	$(PY) convert_dict.py --out $@

$(OUT)/opencc: rebuild_ocd2.sh | $(OUT) toolchain
	sh rebuild_ocd2.sh $@

# The fixture rime_test converts against (see test/opencc/). Not a product: it
# is never packaged, only regenerated for check.
$(OUT)/test-opencc: rebuild_test_opencc.sh | $(OUT) toolchain
	sh rebuild_test_opencc.sh $@

$(OUT):
	mkdir -p $(OUT)

# Byte-for-byte against what is committed. Four separate diffs so a failure
# says which product drifted.
check: all test-opencc
	@fail=0; \
	for f in essay.txt luna_pinyin.dict.yaml; do \
	  if diff -u $(DICT)/$$f $(OUT)/$$f > $(BUILD)/$$f.diff; then \
	    echo "OK   $$f"; \
	  else \
	    echo "DIFF $$f -- see $(BUILD)/$$f.diff"; fail=1; \
	  fi; \
	done; \
	if diff -ru $(DICT)/opencc $(OUT)/opencc > $(BUILD)/opencc.diff; then \
	  echo "OK   opencc/"; \
	else \
	  echo "DIFF opencc/ -- see $(BUILD)/opencc.diff"; fail=1; \
	fi; \
	if diff -ru $(TEST)/opencc $(OUT)/test-opencc > $(BUILD)/test-opencc.diff; then \
	  echo "OK   test/opencc/"; \
	else \
	  echo "DIFF test/opencc/ -- see $(BUILD)/test-opencc.diff"; fail=1; \
	fi; \
	exit $$fail

# Loads dict/ into a real deployment and asserts the engine can use it. Needs
# the engine binary; default path is the in-repo build, override with
# RIME_CONSOLE=/path/to/rime_console.
smoke:
	$(PY) smoke.py --rime-console $${RIME_CONSOLE:-$(abspath $(TOOLS)/../../build/bin/rime_console)}

# Reading audit: read-only. Prints the single-character readings that hijack
# initial-only input; --emit-del pastes them as pinyin_fixes.txt directives.
# MIN_FREQ raises or lowers the character-frequency floor (default 1000).
audit:
	$(PY) audit_readings.py --min-freq $${MIN_FREQ:-1000} $(if $(EMIT),--emit-del,)

# The other two calibration axes: word rows that carry only an archaic reading
# (the modern standard reading cannot type them), and composition blind spots
# from a single character missing its standard reading. With EMIT=1 the output
# is paste-ready add lines -- still to be checked against a dictionary by hand.
audit-words:
	$(PY) audit_readings.py --words --confirmed-only \
	  $(if $(EMIT),--emit-fix,) --limit $${LIMIT:-60}

audit-coverage:
	$(PY) audit_readings.py --coverage --top-words $${TOP_WORDS:-437873} \
	  --min-weight $${MIN_WEIGHT:-100} $(if $(EMIT),--emit-fix,) \
	  --limit $${LIMIT:-60}

package: all
	rm -rf $(PKG)
	mkdir -p $(PKG)/share/term-ime/rime-data
	cp $(OUT)/essay.txt $(OUT)/luna_pinyin.dict.yaml $(PKG)/share/term-ime/rime-data/
	cp -r $(OUT)/opencc $(PKG)/share/term-ime/rime-data/
	cp $(DICT)/LICENSE $(DICT)/VERSION $(PKG)/share/term-ime/rime-data/
	tar -czf $(BUILD)/$(NAME).tar.gz -C $(PKG) share
	cd $(BUILD) && sha256sum $(NAME).tar.gz > $(NAME).tar.gz.sha256
	@echo "$(BUILD)/$(NAME).tar.gz (+ .sha256)"

clean:
	rm -rf $(BUILD)
