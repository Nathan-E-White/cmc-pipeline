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
COPY reference/python /opt/cmc/python
COPY reference/tests /opt/cmc/tests
COPY reference/scripts/reference-solver /opt/cmc/bin/reference-solver
RUN chmod 0755 /opt/cmc/bin/reference-solver
RUN python3 /opt/cmc/python/generate_r0_case_family.py --template /opt/cmc/cases/r0-elastic-displacement-v1.json --output /opt/cmc/cases
RUN test -s /opt/cmc/cases/r0-elastic-displacement-e180-v1.json \
    && test -s /opt/cmc/cases/r0-elastic-displacement-e200-v1.json \
    && test -s /opt/cmc/cases/r0-elastic-displacement-e220-v1.json
RUN python3 /opt/cmc/python/validate_reversible_case.py --case-card /opt/cmc/cases/edge-cracked-plate-reversible-v2.json
RUN python3 /opt/cmc/tests/validate_zero_traction_reversible_regression.py
RUN for level in 'coarse 2 10' 'medium 1 5' 'fine 0.5 2.5'; do \
      set -- $level; \
      python3 /opt/cmc/python/generate_edge_crack_mesh.py \
        --case /opt/cmc/cases/edge-cracked-plate-v1.geo \
        --output "/tmp/opened-crack-$1.msh" \
        --near-size "$2" --far-size "$3" \
        --crack-face-pairs-output "/tmp/opened-crack-$1-pairs.json"; \
      /usr/local/bin/mesh-audit "/tmp/opened-crack-$1.msh" "/tmp/opened-crack-$1-audit.json"; \
      python3 /opt/cmc/python/validate_opened_crack_mesh_artifacts.py \
        --mesh "/tmp/opened-crack-$1.msh" --pairs "/tmp/opened-crack-$1-pairs.json"; \
    done
RUN /opt/cmc/bin/reference-solver verify-case --output /tmp/reference-smoke
RUN test -s /tmp/reference-smoke/mesh-audit.json \
    && test -s /tmp/reference-smoke/environment.json
RUN /opt/cmc/bin/reference-solver solve-case --output /tmp/reference-solve-smoke
RUN test -s /tmp/reference-solve-smoke/displacement.xdmf \
    && test -s /tmp/reference-solve-smoke/solution-summary.json
RUN /opt/cmc/bin/reference-solver converge-case --output /tmp/reference-convergence-smoke
RUN test -s /tmp/reference-convergence-smoke/provenance-convergence.json \
    && test -s /tmp/reference-convergence-smoke/case-visual.svg
RUN /opt/cmc/bin/reference-solver converge-bridged-case --output /tmp/reference-bridged-convergence-smoke
RUN test -s /tmp/reference-bridged-convergence-smoke/provenance-convergence.json \
    && test -s /tmp/reference-bridged-convergence-smoke/case-visual.svg
RUN gmsh /opt/cmc/cases/invalid-edge-plate.geo -2 -format msh41 -o /tmp/invalid-edge-plate.msh
RUN ! /usr/local/bin/mesh-audit /tmp/invalid-edge-plate.msh /tmp/invalid-edge-plate-audit.json
RUN ! /opt/cmc/bin/reference-solver not-a-command

ENTRYPOINT ["/opt/cmc/bin/reference-solver"]
