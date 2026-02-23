# ──────────────────────────────────────────────────────────────────────────────
# Docker release targets for Google Street View Publish WebGUI
#
# Recommended release flow:
#   1. Bump APP_VERSION in app.py
#   2. make docker-test   ← build for local arch + /healthz smoke test
#   3. make docker-push   ← build multi-arch + push both tags to Docker Hub
#
# Other targets:
#   make               – show this help
#   make version       – print the version that will be tagged
#   make check         – list files that would be sent to the Docker daemon
#   make docker-build  – build multi-arch image without pushing
# ──────────────────────────────────────────────────────────────────────────────

# Read the canonical version from app.py – single source of truth
VERSION   := $(shell grep -m1 'APP_VERSION = ' app.py | sed 's/.*"\(.*\)".*/\1/')
IMAGE     := jarrah31/streetview-publish-webgui
PLATFORMS := linux/amd64,linux/arm64

# Detect local CPU architecture for single-platform local test builds
LOCAL_ARCH := $(shell uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')

# Use a different port for smoke tests to avoid clashing with the dev server
TEST_PORT      := 5099
TEST_CONTAINER := streetview-smoke-test

# Default target: show help
.DEFAULT_GOAL := help

.PHONY: help version check docker-build docker-build-local docker-test docker-run docker-stop docker-logs docker-shell docker-push

help:
	@echo ""
	@echo "  Recommended release flow:"
	@echo "    1. Bump APP_VERSION in app.py"
	@echo "    2. make docker-test   ← build locally + /healthz smoke test"
	@echo "    3. make docker-push   ← build multi-arch + push to Docker Hub"
	@echo ""
	@echo "  All targets:"
	@echo "    make version              Print the version read from app.py"
	@echo "    make check                List files that would enter the build context"
	@echo "    make docker-build-local   Build for local arch only, load into daemon"
	@echo "    make docker-test          Build locally + run /healthz smoke test"
	@echo "    make docker-run           Build locally + start container for manual testing"
	@echo "    make docker-stop          Stop and remove the manual test container"
	@echo "    make docker-logs          Tail logs from the running test container"
	@echo "    make docker-shell         Open a shell inside the running test container"
	@echo "    make docker-build         Build multi-arch image (no push)"
	@echo "    make docker-push          Build multi-arch + push :VERSION and :latest"
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

## Build single-arch image for the local machine and load it into the Docker daemon
docker-build-local:
	@echo "→ Building $(IMAGE):$(VERSION) for local arch ($(LOCAL_ARCH))"
	docker buildx build \
		--platform linux/$(LOCAL_ARCH) \
		--load \
		-t $(IMAGE):$(VERSION) \
		-t $(IMAGE):latest \
		.
	@echo "✓ Image loaded into local Docker daemon"

## Build for local arch, start container, verify /healthz responds, then stop
docker-test: docker-build-local
	@echo "→ Cleaning up any leftover test container…"
	@docker rm -f $(TEST_CONTAINER) 2>/dev/null || true
	@echo "→ Starting test container on port $(TEST_PORT)…"
	@docker run -d --name $(TEST_CONTAINER) \
		-e GOOGLE_CLIENT_ID=smoke-test \
		-e GOOGLE_CLIENT_SECRET=smoke-test \
		-e GOOGLE_MAPS_API_KEY=smoke-test \
		-e REDIRECT_URI=http://localhost:$(TEST_PORT)/oauth2callback \
		-e FLASK_SECRET_KEY=smoke-test-secret \
		-p $(TEST_PORT):5001 \
		$(IMAGE):$(VERSION)
	@echo "→ Waiting for /healthz to respond (up to 30 s)…"
	@PASS=0; \
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		response=$$(curl -sf http://localhost:$(TEST_PORT)/healthz 2>/dev/null); \
		if echo "$$response" | grep -q '"ok"'; then \
			echo "✓ /healthz responded: $$response"; \
			PASS=1; \
			break; \
		fi; \
		printf "  (%s/15) not ready yet, retrying in 2 s…\n" "$$i"; \
		sleep 2; \
	done; \
	if [ "$$PASS" = "1" ]; then \
		docker stop $(TEST_CONTAINER) > /dev/null; \
		docker rm  $(TEST_CONTAINER) > /dev/null 2>&1 || true; \
		echo "✓ Smoke test passed – safe to run: make docker-push"; \
	else \
		echo "✗ Smoke test FAILED – container did not respond within 30 s"; \
		echo "  Container logs:"; \
		docker logs $(TEST_CONTAINER); \
		docker stop $(TEST_CONTAINER) > /dev/null 2>&1 || true; \
		docker rm  $(TEST_CONTAINER) > /dev/null 2>&1 || true; \
		exit 1; \
	fi

## Build locally and start container for manual browser testing (stays running)
docker-run: docker-build-local
	@echo "→ Cleaning up any leftover test container…"
	@docker rm -f $(TEST_CONTAINER) 2>/dev/null || true
	@echo "→ Starting container on port $(TEST_PORT)…"
	@docker run -d --name $(TEST_CONTAINER) \
		-e GOOGLE_CLIENT_ID=smoke-test \
		-e GOOGLE_CLIENT_SECRET=smoke-test \
		-e GOOGLE_MAPS_API_KEY=smoke-test \
		-e REDIRECT_URI=http://localhost:$(TEST_PORT)/oauth2callback \
		-e FLASK_SECRET_KEY=smoke-test-secret \
		-p $(TEST_PORT):5001 \
		$(IMAGE):$(VERSION)
	@echo "→ Waiting for container to become ready…"
	@for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do \
		if curl -sf http://localhost:$(TEST_PORT)/healthz > /dev/null 2>&1; then \
			break; \
		fi; \
		printf "  (%s/15) not ready yet, retrying in 2 s…\n" "$$i"; \
		sleep 2; \
	done
	@echo ""
	@echo "  ✓ Container is running"
	@echo "  → Open in browser : http://localhost:$(TEST_PORT)"
	@echo ""
	@echo "  Note: dummy credentials are in use – OAuth login will not work."
	@echo "        Pages, layout, and static assets can be tested normally."
	@echo ""
	@echo "  Useful commands:"
	@echo "    make docker-logs    tail live container logs (Ctrl-C to stop)"
	@echo "    make docker-shell   open a shell inside the container"
	@echo "    make docker-stop    stop and remove the container when done"
	@echo ""

## Stop and remove the manual test container
docker-stop:
	@echo "→ Stopping $(TEST_CONTAINER)…"
	@docker stop $(TEST_CONTAINER) > /dev/null 2>&1 || true
	@docker rm   $(TEST_CONTAINER) > /dev/null 2>&1 || true
	@echo "✓ Container stopped and removed"

## Tail live logs from the running test container (Ctrl-C to exit)
docker-logs:
	docker logs -f $(TEST_CONTAINER)

## Open an interactive shell inside the running test container
docker-shell:
	docker exec -it $(TEST_CONTAINER) /bin/bash || docker exec -it $(TEST_CONTAINER) /bin/sh

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
