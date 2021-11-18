# Copyright 2019 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
include $(HDCTOOLS_DIR)/defs/definitions.mk
include $(HDCTOOLS_DIR)/defs/utilities.mk

SCRIPTDIR       = /etc/bash_completion.d
SCRIPT_DEST_DIR = $(DESTDIR)$(SCRIPTDIR)

SCRIPT_SRC = $(notdir $(wildcard $(HDCTOOLS_SOURCE_DIR)/*.bash))
SCRIPT_DST = $(addprefix $(SCRIPT_DEST_DIR)/, $(subst .bash,,$(SCRIPT_SRC)))

$(SCRIPT_DEST_DIR)/%: $(HDCTOOLS_SOURCE_DIR)/%.bash
	$(MESSAGE) "Copying $(notdir $@)"
	$(MKDIR) -p `dirname $@`
	$(CP) $< $@

all:
	true

install: $(SCRIPT_DST)
