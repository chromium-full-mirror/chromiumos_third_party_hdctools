# Copyright 2011 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

export HDCTOOLS_DIR = $(shell pwd)
include $(HDCTOOLS_DIR)/defs/definitions.mk

SUBDIRS		= ec3po lib measurement_tools tests/c_legacy servo servo_updater usbkm232
ifdef EXTRA_DIRS
SUBDIRS		+= $(EXTRA_DIRS)
endif

SUBDIRS_INSTALL	= $(foreach var,$(SUBDIRS),$(var)-install)

all:    $(SUBDIRS)
install:   $(SUBDIRS_INSTALL)
clean:
	@rm -rf $(HDCTOOLS_BUILD_DIR) servo/sversion.py

$(SUBDIRS): ver
	@$(call remake,Building,$@,all)

# No subdirectory 'install' target needs any dependency on building
# (such as 'all') The explicit dependency on 'all' here ensures that
# the full source tree is built just once.
$(SUBDIRS_INSTALL):	all
	@$(call remake,Installing,$(subst -install,,$@),install)

.PHONY:	ver $(SUBDIRS) $(SUBDIRS_INSTALL)

ver:
	# Generate the sversion file in the same directory as setup.py so that
	# versioning can happen on build-time.
	$(HDCTOOLS_DIR)/getversion.sh > $(HDCTOOLS_DIR)/servo/sversion.py;

src:	lib
test:	src lib
tests/c_legacy: lib
