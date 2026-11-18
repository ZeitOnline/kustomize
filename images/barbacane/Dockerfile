# Barbacane for the `barbacane-sidecar` component: the upstream binary plus the
# plugins our projects use, on our own distroless base. Projects compile their
# spec with `/barbacane` and `/plugins` from here and run the artefact on this
# image; see README.md.
#
# A new upstream version needs a new `version` too (`<upstream>-1`).
FROM ghcr.io/barbacane-dev/barbacane:0.12.4@sha256:4cd621f7d705ddf56e9eebbed8a8555ed547a6e633e404c802932de7ca48c464 AS upstream

# wasm is the same on every platform, so this stage runs natively on the build
# machine and the multi-platform build needs no emulation
FROM --platform=$BUILDPLATFORM debian:12-slim@sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc AS plugins
RUN apt-get update \
    && apt-get install --yes --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
# the plugins in `plugin-checksums.txt` come from the release of the upstream
# part of `version`, which CI checks against the binary; the hashes are ours,
# as releases can change, so new ones come with a new `version`
COPY version plugin-checksums.txt /tmp/
WORKDIR /plugins
RUN set -eu; \
    version=$(cut -d- -f1 /tmp/version); \
    base="https://github.com/barbacane-dev/barbacane/releases/download/v$version"; \
    for p in $(cut -d' ' -f3 /tmp/plugin-checksums.txt); do \
      curl -fsSLO "$base/$p"; \
    done; \
    sha256sum --strict -c /tmp/plugin-checksums.txt

# Debian 13: distroless' Debian 12 image still ships libssl3 3.0.20 (7 fixable
# High); the upstream binary runs unchanged on the newer glibc
FROM gcr.io/distroless/cc-debian13:nonroot@sha256:cb87acc574abe719b6e5c547384defa2f7b1f24af9605d3f618cf852495d8be2 AS barbacane
COPY --from=upstream /barbacane /barbacane
COPY --from=plugins /plugins /plugins
EXPOSE 8080
ENTRYPOINT ["/barbacane"]
CMD ["serve", "--artifact", "/config/api.bca"]

# compiles a spec using every plugin, with the image's own binary
FROM barbacane AS testing
COPY test /test
CMD ["compile", "--manifest", "/test/barbacane.yaml", "--spec", "/test/api.yaml", \
     "--output", "/tmp/api.bca"]
