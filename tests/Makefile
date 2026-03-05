# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		=
SUBDIRS_INSTALL	=
PYTHON_SRC	= $(shell cd $(HDCTOOLS_SOURCE_DIR); find . -type f -name '*.py' | sed 's/^\.\///')
PYTHON_DST	= $(addprefix $(THIS_BUILD_DIR)/, $(PYTHON_SRC))

$(THIS_BUILD_DIR)/%.py: $(HDCTOOLS_SOURCE_DIR)/%.py
	$(MESSAGE) "Copying $(notdir $@)"
	mkdir -p $(@D)
	$(CP) $< $@

all: 		$(PYTHON_DST)

install:			# NOP
