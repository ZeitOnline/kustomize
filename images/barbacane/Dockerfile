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
# the plugins come from the release of the upstream part of `version`, which CI
# checks against the binary; the release's `plugin-checksums.txt` verifies them
COPY version /tmp/version
ARG PLUGINS="http-upstream cors oidc-auth cel request-transformer ai-proxy"
WORKDIR /plugins
RUN set -eu; \
    version=$(cut -d- -f1 /tmp/version); \
    base="https://github.com/barbacane-dev/barbacane/releases/download/v$version"; \
    curl -fsSLO "$base/plugin-checksums.txt"; \
    for p in $PLUGINS; do \
      curl -fsSLO "$base/$p.wasm"; \
      grep " $p.wasm\$" plugin-checksums.txt > "$p.sha256"; \
      sha256sum -c "$p.sha256"; \
      rm "$p.sha256"; \
    done; \
    rm plugin-checksums.txt

FROM gcr.io/distroless/cc-debian12:nonroot@sha256:9dac0a79194e45a7da0158a9c6da57b217585af0786db3845d1f0ec1a0dd182f AS barbacane
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
