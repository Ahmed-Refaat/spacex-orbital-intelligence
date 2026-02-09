.PHONY: download-kernels test test-anise clean-kernels

# Download ANISE kernels
download-kernels:
	@echo "Downloading ANISE kernels..."
	@mkdir -p kernels
	@cd kernels && \
	curl -O http://public-data.nyxspace.com/anise/de440s.bsp && \
	curl -O http://public-data.nyxspace.com/anise/v0.7/pck08.pca && \
	echo "✓ Kernels downloaded ($(shell du -sh kernels | cut -f1))"

# Run ANISE tests
test-anise:
	@source venv/bin/activate && pytest tests/unit/test_anise_client.py -v --tb=short

# Run all tests
test:
	@source venv/bin/activate && pytest tests/ -v

# Clean kernels (for fresh download)
clean-kernels:
	@rm -rf kernels/*.bsp kernels/*.pca kernels/*.bpc
	@echo "✓ Kernels cleaned"

# Benchmark ANISE performance
benchmark:
	@source venv/bin/activate && pytest tests/unit/test_anise_client.py --benchmark-only -v
