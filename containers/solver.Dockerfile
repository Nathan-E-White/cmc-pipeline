FROM dolfinx/dolfinx:stable@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8

USER root

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends \
        cmake \
        g++ \
        gmsh \
        libgmsh-dev \
        ninja-build \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/cmc

COPY reference/cpp /opt/cmc/cpp
RUN cmake -S /opt/cmc/cpp -B /opt/cmc/build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /opt/cmc/build \
    && ctest --test-dir /opt/cmc/build --output-on-failure \
    && cmake --install /opt/cmc/build

COPY reference/cases /opt/cmc/cases
COPY reference/scripts/reference-solver /opt/cmc/bin/reference-solver
RUN chmod 0755 /opt/cmc/bin/reference-solver
RUN /opt/cmc/bin/reference-solver verify-case --output /tmp/reference-smoke \
    && test -s /tmp/reference-smoke/mesh-audit.json \
    && test -s /tmp/reference-smoke/environment.json \
    && gmsh /opt/cmc/cases/invalid-edge-plate.geo -2 -format msh41 -o /tmp/invalid-edge-plate.msh \
    && ! /usr/local/bin/mesh-audit /tmp/invalid-edge-plate.msh /tmp/invalid-edge-plate-audit.json \
    && ! /opt/cmc/bin/reference-solver not-a-command

ENTRYPOINT ["/opt/cmc/bin/reference-solver"]
