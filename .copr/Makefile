# COPR Makefile for CoreFreq akmod
# This file goes in .copr/Makefile in your COPR repo

srpm:
	# Download CoreFreq source
	wget -O corefreq-2.0.8.tar.gz https://github.com/cyring/CoreFreq/archive/refs/tags/2.0.8.tar.gz
	
	# Create SRPM
	rpmbuild -bs \
		--define "_sourcedir $(CURDIR)" \
		--define "_specdir $(CURDIR)" \
		--define "_srcrpmdir $(outdir)" \
		corefreq-akmod.spec

.PHONY: srpm