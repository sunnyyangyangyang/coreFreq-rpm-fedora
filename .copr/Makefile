# COPR Makefile for CoreFreq akmod - Fixed Version
# This file should be placed at .copr/Makefile in your COPR repository

VERSION = 2.1.0
RELEASE = 1
SPEC_FILE = corefreq-akmod.spec

# COPR requires this target
srpm: $(SPEC_FILE) corefreqd.service Makefile.akmod
	@echo "Building SRPM for CoreFreq akmod..."
	
	# Download source if not present
	@if [ ! -f corefreq-$(VERSION).tar.gz ]; then \
		echo "Downloading CoreFreq $(VERSION)..."; \
		wget -O corefreq-$(VERSION).tar.gz \
			https://github.com/cyring/CoreFreq/archive/refs/tags/$(VERSION).tar.gz; \
	fi
	
	# Verify all required source files are present
	@for file in $(SPEC_FILE) corefreqd.service Makefile.akmod; do \
		if [ ! -f "$$file" ]; then \
			echo "ERROR: Required file $$file not found!"; \
			echo "Available files:"; \
			ls -la; \
			exit 1; \
		fi; \
	done
	
	# Verify downloaded source
	@if [ ! -f corefreq-$(VERSION).tar.gz ]; then \
		echo "ERROR: Source tarball corefreq-$(VERSION).tar.gz not found!"; \
		exit 1; \
	fi
	
	# Verify tarball contents (basic check)
	@if ! tar -tzf corefreq-$(VERSION).tar.gz | head -5 | grep -q "CoreFreq-$(VERSION)"; then \
		echo "ERROR: Source tarball appears corrupted or has unexpected structure"; \
		tar -tzf corefreq-$(VERSION).tar.gz | head -10; \
		exit 1; \
	fi
	
	# Create source RPM with verbose output
	@echo "Creating SRPM..."
	@echo "Source files:"
	@ls -la *.service *.akmod $(SPEC_FILE) corefreq-$(VERSION).tar.gz 2>/dev/null || true
	
	rpmbuild -bs \
		--define "_sourcedir $(CURDIR)" \
		--define "_specdir $(CURDIR)" \
		--define "_srcrpmdir $(outdir)" \
		--define "_tmppath /tmp" \
		--define "_topdir /tmp/rpmbuild" \
		$(SPEC_FILE)
	
	@echo "SRPM created successfully in $(outdir)"
	@if [ -d "$(outdir)" ]; then \
		echo "Contents of output directory:"; \
		ls -la "$(outdir)"; \
	fi

# Development targets (not used by COPR but helpful for testing)
.PHONY: srpm clean test-spec lint-spec help download verify

clean:
	rm -f *.tar.gz *.rpm *.log
	rm -rf rpmbuild/ /tmp/rpmbuild/

download:
	@echo "Downloading CoreFreq $(VERSION)..."
	wget -O corefreq-$(VERSION).tar.gz \
		https://github.com/cyring/CoreFreq/archive/refs/tags/$(VERSION).tar.gz

verify: download
	@echo "Verifying downloaded source..."
	@if tar -tzf corefreq-$(VERSION).tar.gz | head -5 | grep -q "CoreFreq-$(VERSION)"; then \
		echo "✅ Source tarball looks good"; \
		echo "Contents (first 10 entries):"; \
		tar -tzf corefreq-$(VERSION).tar.gz | head -10; \
	else \
		echo "❌ Source tarball structure unexpected"; \
		tar -tzf corefreq-$(VERSION).tar.gz | head -10; \
		exit 1; \
	fi

test-spec: verify
	@echo "Testing spec file syntax..."
	rpmbuild --nobuild \
		--define "_sourcedir $(CURDIR)" \
		--define "_topdir /tmp/rpmbuild" \
		$(SPEC_FILE)

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
	@echo "  download   - Download source tarball"
	@echo "  verify     - Verify downloaded source"
	@echo "  test-spec  - Test spec file syntax"
	@echo "  lint-spec  - Lint spec file with rpmlint"
	@echo "  help       - Show this help"
	@echo ""
	@echo "Files required for COPR build:"
	@echo "  $(SPEC_FILE) - RPM spec file"
	@echo "  corefreqd.service - systemd service file"
	@echo "  Makefile.akmod - akmod-compatible Makefile"