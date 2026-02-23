# ──────────────────────────────────────────────────────────────────────────────
# Docker release targets for Google Street View Publish WebGUI
#
# Usage:
#   make               – show help
#   make version       – print the version that will be tagged
#   make check         – show what files would be sent to the Docker daemon
#   make docker-build  – build multi-arch image locally (no push)
#   make docker-push   – build AND push to Docker Hub
# ──────────────────────────────────────────────────────────────────────────────

# Read the canonical version from app.py – single source of truth
VERSION   := $(shell grep -m1 'APP_VERSION = ' app.py | sed 's/.*"\(.*\)".*/\1/')
IMAGE     := jarrah31/streetview-publish-webgui
PLATFORMS := linux/amd64,linux/arm64

# Default target: show help
.DEFAULT_GOAL := help

.PHONY: help version check docker-build docker-push

help:
	@echo ""
	@echo "  make version       Print the version read from app.py (APP_VERSION)"
	@echo "  make check         List files that would be sent to the Docker daemon"
	@echo "  make docker-build  Build multi-arch image locally (no push)"
	@echo "  make docker-push   Build multi-arch image and push to Docker Hub"
	@echo ""
	@echo "  Current version : $(VERSION)"
	@echo "  Image           : $(IMAGE)"
	@echo "  Platforms       : $(PLATFORMS)"
	@echo ""

## Print the version that will be tagged
version:
	@echo "$(VERSION)"

## List every file that would be included in the Docker build context.
## Nothing in this list should be a secret – if something looks wrong,
## update .dockerignore before running docker-push.
check:
	@echo "─── Docker build context (files NOT excluded by .dockerignore) ───"
	@git ls-files --cached --others --exclude-standard | \
	  while IFS= read -r f; do \
	    docker run --rm -v "$(PWD):/src" alpine sh -c \
	      "cd /src && cat .dockerignore | grep -qxF \"$$f\" || echo $$f" 2>/dev/null || true; \
	  done
	@echo ""
	@echo "Tip: a simpler check – build context size appears at the start of"
	@echo "     'docker buildx build'. If it looks large, run this target again."

## Build multi-arch image locally without pushing
docker-build:
	@echo "→ Building $(IMAGE):$(VERSION) (no push)"
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(IMAGE):$(VERSION) \
		-t $(IMAGE):latest \
		.
	@echo "✓ Build complete: $(IMAGE):$(VERSION)"

## Build multi-arch image and push both the versioned tag and :latest
docker-push:
	@echo "→ Building and pushing $(IMAGE):$(VERSION) + $(IMAGE):latest"
	docker buildx build \
		--platform $(PLATFORMS) \
		-t $(IMAGE):$(VERSION) \
		-t $(IMAGE):latest \
		--push \
		.
	@echo "✓ Pushed: $(IMAGE):$(VERSION)"
	@echo "✓ Pushed: $(IMAGE):latest"
