# COPR Makefile for CoreFreq akmod
# This file should be placed at .copr/Makefile in your COPR repository

VERSION = 2.0.8
RELEASE = 1.alpha4
SPEC_FILE = corefreq-akmod.spec

# COPR requires this target
srpm: $(SPEC_FILE) corefreqd.service Makefile.akmod Makefile.kernel
	@echo "Building SRPM for CoreFreq akmod..."
	
	# Download source if not present
	@if [ ! -f corefreq-$(VERSION).tar.gz ]; then \
		echo "Downloading CoreFreq $(VERSION)..."; \
		wget -O corefreq-$(VERSION).tar.gz \
			https://github.com/cyring/CoreFreq/archive/refs/tags/$(VERSION).tar.gz; \
	fi
	
	# Verify all required source files are present
	@for file in $(SPEC_FILE) corefreqd.service Makefile.akmod Makefile.kernel; do \
		if [ ! -f "$file" ]; then \
			echo "ERROR: Required file $file not found!"; \
			exit 1; \
		fi; \
	done
	
	# Verify checksum (optional but recommended)
	@if [ -f checksums.txt ]; then \
		echo "Verifying checksum..."; \
		sha256sum -c checksums.txt || (echo "Checksum verification failed!" && exit 1); \
	fi
	
	# Create source RPM
	@echo "Creating SRPM..."
	rpmbuild -bs \
		--define "_sourcedir $(CURDIR)" \
		--define "_specdir $(CURDIR)" \
		--define "_srcrpmdir $(outdir)" \
		--define "_tmppath /tmp" \
		$(SPEC_FILE)
	
	@echo "SRPM created successfully in $(outdir)"

# Development targets (not used by COPR but helpful for testing)
.PHONY: srpm clean test-spec lint-spec help

clean:
	rm -f *.tar.gz *.rpm *.log
	rm -rf rpmbuild/

test-spec:
	@echo "Testing spec file syntax..."
	rpmbuild --nobuild $(SPEC_FILE)

lint-spec:
	@echo "Linting spec file..."
	@if command -v rpmlint >/dev/null; then \
		rpmlint $(SPEC_FILE); \
	else \
		echo "rpmlint not available - install with: dnf install rpmlint"; \
	fi

help:
	@echo "COPR Makefile for CoreFreq akmod"
	@echo ""
	@echo "Targets:"
	@echo "  srpm       - Build source RPM (required by COPR)"
	@echo "  clean      - Clean build artifacts"  
	@echo "  test-spec  - Test spec file syntax"
	@echo "  lint-spec  - Lint spec file with rpmlint"
	@echo "  help       - Show this help"