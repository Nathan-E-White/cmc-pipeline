**AI Acceleration of Non-Oxide CMC Analysis for TPS applications**  
  
**CMC:**	Ceramic Metal Composite  
**TPS: **	Thermal Protection System  
  
Non-Oxide Ceramic Metal Composite (CMC), including fiber coating, for Thermal Protection System applications  
  
 ++[Ceramic matrix composites (CMCs)](https://en.wikipedia.org/wiki/Ceramic_matrix_composite)++ are ceramic fibers held within a ceramic matrix. Due to the weak, but carefully tuned, bond between the matrix and fibers the composites exhibits some ductility and damage tolerance far exceeding standard (monolithic) ceramics. As ceramics, they are extraordinarily good at withstanding heat and they are lighter than metals that are used for high temperature applications. They are formed in several ways, though the most common seem to be starting from a polymer tape with ceramic fiber embedded, burning out the polymer in a vacuum furnace after the part is constructed, and then infiltrating a liquid or gas to form the ceramic matrix. This is referred to in the job posting as CVD/CVI (chemical vapor deposition/chemical vapor infiltration) and PIP (polymer infiltration and pyrolysis) Several gas turbine companies, most notably GE Aviation, are investing heavily in implementing CMCs to save weight and increase engine temperature (for thermo efficiency). 1 part made of CMC is currently flying on the CFM LEAP engine used by the A320NEO and 737MAX aircraft.   
  
  
## 1. System Architecture & Data Topology  
## This architecture decouples heavy, high-latency multi-physics data generation from the ultra-low-latency interactive client layer. The backend acts as an automated ingestion and synthetic data generation machine, while the frontend serves as an operational terminal for real-time visualization and surrogate estimation.  
```
+---------------------------------------------------------------------------------+
|                                 BACKEND PIPELINE                                |
|                                                                                 |
|  [NDE / CAD Scan] --> (Argo Workflow DAG)                                       |
|                               |                                                 |
|                               +--> [Step 1: SnappyHexMesh Voxelization]         |
|                               +--> [Step 2: Multiscale FEM / J-Integral Core]  |
|                               +--> [Step 3: FNO Model Drift Adjudication]      |
|                                                                                 |
|                               |                                                 |
|                               v                                                 |
|                 [PostgreSQL / Object Storage]                                   |
+---------------------------------------------------------------------------------+
                                |
                                | REST APIs / JSON Payloads
                                v
+---------------------------------------------------------------------------------+
|                                CLIENT DASHBOARD                                 |
|                                                                                 |
|  [Web UI (Three.js)] <--> [ONNX Runtime Client Session] (Real-time adjustments)  |
+---------------------------------------------------------------------------------+

```
## Infrastructure Layer Separation  

| Component | Responsibility | Technology Stack | Compute Profile |
| -------------- | --------------------------------------------------------------------------------------- | ------------------------------------------ | ------------------------------ |
| Data Ingestion | Automate NDE raw scanner file parsing and format normalization. | Kubernetes CronJobs / S3 Event Triggers | Low Compute / High I/O |
| Pipeline Core | Orchestrate multiscale meshing, finite element execution, and training loops. | Argo Workflows (DAG Engine) | High Compute (CPU/GPU Cluster) |
| Persistence | Store mesh topology files, tensor matrices, and material metadata. | PostgreSQL & AWS S3 / MinIO Object Storage | High Storage Bound |
| Serving Layer | Expose processed simulation histories and model weights to the web interface. | FastAPI / Python Uvicorn | Low Latency / Persistent |
| Client UI | Render structural deformations, crack propagation paths, and interactive slider inputs. | Three.js WebGL / ONNX Runtime Web | Client GPU Accelerated |
  
****2. Backend Orchestration: Argo Workflow Specification****  
## The following manifest defines a production-grade container-native DAG. It isolates the meshing code from the finite element mechanics and incorporates data locality optimizations using a shared ephemeral volume.  
## yaml  
```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: cmc-fracture-pipeline-
  namespace: simulation-core
spec:
  entrypoint: cmc-multiscale-dag
  volumeClaimTemplates:
  - metadata:
      name: shared-scratchpad
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 100Gi
      storageClassName: nvme-fast-scratch

  templates:
  - name: cmc-multiscale-dag
    dag:
      tasks:
      - name: mesh-generation
        template: generate-voxel-mesh
        arguments:
          parameters: [{name: "cad-id", value: "{{workflow.parameters.cad-id}} Erin"}]

      - name: parallel-fem-solver
        dependencies: [mesh-generation]
        template: execute-j-integral-fem
        arguments:
          parameters: [{name: "mesh-artifact", value: "{{tasks.mesh-generation.outputs.parameters.mesh-path}}"}]

      - name: surrogate-inference
        dependencies: [mesh-generation]
        template: evaluate-fno-surrogate
        arguments:
          parameters: [{name: "mesh-artifact", value: "{{tasks.mesh-generation.outputs.parameters.mesh-path}}"}]

      - name: evaluate-accuracy-drift
        dependencies: [parallel-fem-solver, surrogate-inference]
        template: adjudicate-model-drift
        arguments:
          parameters:
          - {name: "fem-data", value: "{{tasks.parallel-fem-solver.outputs.parameters.results-path}}"}
          - {name: "fno-data", value: "{{tasks.surrogate-inference.outputs.parameters.results-path}}"}

  # Step 1: Pre-processing & Volumetric Meshing Task
  - name: generate-voxel-mesh
    container:
      image: registry.spacex.corp/simulation/mesher:v2.1
      command: [python, /app/mesh_generator.py]
      args: ["--id", "{{inputs.parameters.cad-id}}"]
      volumeMounts:
      - name: shared-scratchpad
        mountPath: /data/scratch
    outputs:
      parameters:
      - name: mesh-path
        valueFrom: {path: /data/scratch/mesh_output_path.txt}

  # Step 2: High-Fidelity Finite Element Solver Track
  - name: execute-j-integral-fem
    container:
      image: registry.spacex.corp/simulation/fem-solver:v5.0
      command: [/opt/solvers/fem_core]
      args: ["--input-mesh", "{{inputs.parameters.mesh-artifact}}", "--output-dir", "/data/scratch/fem_results"]
      resources:
        requests:
          cpu: "16"
          memory: "64Gi"
      volumeMounts:
      - name: shared-scratchpad
        mountPath: /data/scratch
    outputs:
      parameters:
      - name: results-path
        value: "/data/scratch/fem_results/matrix_fields.bin"

  # Step 3: Fast Neural Operator Evaluation Track
  - name: evaluate-fno-surrogate
    container:
      image: registry.spacex.corp/ai/fno-evaluator:v1.4
      command: [python, /models/fno_inference.py]
      args: ["--mesh", "{{inputs.parameters.mesh-artifact}}", "--out", "/data/scratch/fno_results"]
      resources:
        limits:
          ://nvidia.com: "1"
      volumeMounts:
      - name: shared-scratchpad
        mountPath: /data/scratch
    outputs:
      parameters:
      - name: results-path
        value: "/data/scratch/fno_results/prediction_fields.onnx_tensor"

  # Step 4: Adjudication, Database Logging & Web Optimization
  - name: adjudicate-model-drift
    container:
      image: registry.spacex.corp/simulation/adjudicator:v1.0
      command: [python, /app/compare_and_upload.py]
      args:
      - "--fem-src"
      - "{{inputs.parameters.fem-data}}"
      - "--fno-src"
      - "{{inputs.parameters.fno-data}}"
      volumeMounts:
      - name: shared-scratchpad
        mountPath: /data/scratch

```
Use code with caution.  
  
## 3. Frontend Integration & Data Contracts  
## To decouple client displays from data parsing, JSON serialization schemas standardize how the frontend requests historical continuum arrays from the FastAPI backend layer.  
## REST API: Fetch Static Continuum Mesh Data  
* **Endpoint:** /api/v1/simulation/mesh/{component_id}  
* **Method:** GET  
* **Response Payload Structure:**  
## json  
```
{
  "component_id": "SR-TPS-042",
  "matrix_architecture": "sic_sic",
  "node_count": 640000,
  "vertex_positions": [
    -1.5, 0.0, 0.0,
    -1.45, 0.1, -0.02,
    "..."
  ],
  "fiber_indices": [
    [0, 12, 24],
    [36, 48, 60]
  ]
}

```
Use code with caution.  
  
## REST API: Post Live Verification Runs to Backend Database  
* **Endpoint:** /api/v1/simulation/verify  
* **Method:** POST  
* **Request Payload Structure:**  

| Parameter Name | Data Type | Example Value | Description |
| --------------------- | --------- | ------------- | ----------------------------------------------------------- |
| component_id | String | "SR-TPS-042" | Unique identifier of the specific hardware component asset. |
| thermal_gradient | Float | 145.5 | Operational temperature slope constraint in °C/mm. |
| shear_load | Float | 65.2 | Active aerodynamic mechanical force vector in kilonewtons. |
| coating_shear_limit | Float | 60.0 | Experimentally derived interface failure threshold in MPa. |
| fno_margin_prediction | Float | 0.42 | The client-side computed local safety margin score. |
  
****4. Hybrid Client/Server Inference Strategy****  
## To bypass network latency during real-time human-in-the-loop engineering reviews, the system balances computation between localized browser contexts and remote server clusters.  
```
                +--------------------------------------------------+
                | Is Calculation Target < 100 Milliseconds?        |
                +--------------------------------------------------+
                                  /              \
                                 /                \
                               YES                 NO
                               /                    \
                              v                      v
               +-----------------------+   +-----------------------+
               | CLIENT-SIDE INFERENCE |   | SERVER-SIDE INFERENCE |
               |                       |   |                       |
               | - ONNX Runtime Web    |   | - Remote Argo Engine  |
               | - Local GPU Thread    |   | - Cluster Scale Core  |
               | - Instant Re-Mapping  |   | - Ground Truth Audit  |
               +-----------------------+   +-----------------------+

```
## Execution Boundary Allocations  

| Capability Vector | Local Web Execution (ONNX Web) | Cluster Execution (Argo Workflows) |
| ----------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Target Latency | < 10 milliseconds (Microsecond instant) | 4 to 15 seconds (Batch schedule floor) |
| Compute Location | Local Client Workstation Graphics Hardware | Remote Kubernetes Node Pools (HPC Core) |
| Primary Objective | Immediate interactive slider rendering and qualitative trend analysis. | Rigorous mechanical verification and validation audits for flight readiness. |
| Memory Allocation | Limited by client browser sandbox limits (~2-4 GB) | Scalable up to host server node maximums (>512 GB RAM) |
| Trigger Mechanism | Native Javascript UI event handlers (input, change) | Explicit user button click issuing an authenticated API request |
  
  
  
  
  
  
**Architectural Blueprint Finalized**  
This comprehensive system specification establishes a strong foundation for your architectural pitch. It frames your project around the technical language of distributed container networks and scalable data infrastructure that platform engineers evaluate.  
Now that the system topology and workflow blueprints are locked in, we can move back into **Code Mode**. I will compile the complete interactive frontend mockup—fully updated to reflect **Option C** (\(\text{SiC/SiC}\) microstructural fracture continuum, adjustable fiber coating shear limits, and simulated FNO execution tracks)—into a standalone executable file so you have a functional dashboard ready to demonstrate.  
  
  
  
  
  
  
## 1. Executive Summary & Pitch Alignment  
This architectural blueprint outlines an end-to-end software platform designed for the **SpaceX Non-Destructive Evaluation (NDE) & Materials Software** team. The platform balances high-fidelity batch simulation mechanics with real-time interactive tooling, fulfilling the core preferences outlined in the team's job specifications. [++[1](https://talents.vaia.com/companies/spacex/materials-engineer-lab-34203944/)++]  
## Core Strategic Pillars  
* **The Problem:** Traditional Finite Element Analysis (FEA) and J-Integral fracture mechanics require heavy multi-pass numerical relaxation grids, creating a turnaround bottleneck during rapid post-flight vehicle evaluations. [++[1](https://www.basenor.com/blogs/news/musk-declares-starship-heat-shield-problem-solved-after-flight-13)++, ++[2](https://www.facebook.com/groups/436711088832255/posts/915127854323907/)++]  
* **The AI/ML Solution:** Utilizing a Fourier Neural Operator (FNO) surrogate model accelerates crack propagation boundary predictions from minutes down to milliseconds, significantly reducing inspection overhead.  
* **Production Stack Integration:** Decoupling the batch pipeline (orchestrated via container-native toolsets) from the presentation viewer (rendered via browser-based frameworks) satisfies both multi-region data engineering constraints and low-latency visualization needs. [++[1](https://www.dice.com/job-detail/7f0b28a2-b675-4c12-9507-22cb93140d95)++]  
## 2. Decoupled System Topology  
The platform separates long-running, resource-intensive computational physics from fast, interactive client-side operations to preserve cluster performance and user experience. [++[1](https://akuity.io/blog/argo-101-what-is-argo)++]  

| Architectural Attribute | Frontend Client Viewer | Backend Compute Pipeline |
| ----------------------- | -------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Primary Responsibility | Interactive parameter tuning, real-time stress visualization, flight telemetry review. | Synthetic data generation, high-fidelity FEM verification, neural network surrogate training. |
| Latency Target | Sub-16 milliseconds (Consistent 60 FPS viewport rendering). | Asynchronous batch execution (Minutes to hours depending on grid size). |
| Compute Environment | Client browser engine (WebGL / Client-side CPU & GPU memory allocation). | Distributed Kubernetes Cluster (High-performance multi-node enterprise GPUs). |
| Core Technologies | Three.js, HTML5 Control Canvas, ONNX Runtime Web API. | Argo Workflows, Docker/Containerd, PyTorch, C++ Multiscale Solvers. |
|  |  |  |
  
****3. Argo Workflow Orchestration****  
Backend data preparation, structural parsing, and surrogate validation loops are modeled as a container-native Directed Acyclic Graph (DAG) using Argo Workflows. [++[1](https://www.alphaxiv.org/abs/2603.24206)++]  
## yaml  
```
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: cmc-fracture-mesh-pipeline-
  namespace: ndesim-solvers
spec:
  entrypoint: cmc-simulation-dag
  volumeClaimTemplates:
  - metadata:
      name: simulation-shared-nvme
    spec:
      accessModes: [ "ReadWriteMany" ]
      resources:
        requests:
          storage: 100Gi
  templates:
  - name: cmc-simulation-dag
    dag:
      tasks:
      - name: parse-nde-scan
        template: process-sensor-geometry
      - name: execute-fno-surrogate
        dependencies: [parse-nde-scan]
        template: run-fno-inference
      - name: execute-fea-verification
        dependencies: [parse-nde-scan]
        template: run-high-fidelity-fea
      - name: adjudicate-and-export
        dependencies: [execute-fno-surrogate, execute-fea-verification]
        template: bundle-visualization-assets

  - name: process-sensor-geometry
    container:
      image: registry.spacex.corp/ndesim/mesh-util:v1.2
      command: [python3, /app/mesh_voxelizer.py]
      args: ["--input-src", "/mnt/data/scan_source"]
      volumeMounts:
      - name: simulation-shared-nvme
        mountPath: /mnt/data

  - name: run-fno-inference
    container:
      image: registry.spacex.corp/ndesim/fno-surrogate:v2.0
      command: [torchrun, /app/fno_predict.py]
      volumeMounts:
      - name: simulation-shared-nvme
        mountPath: /mnt/data

  - name: run-high-fidelity-fea
    container:
      image: registry.spacex.corp/ndesim/fea-solver:v5.1
      command: [/app/bin/multiscale_solver]
      volumeMounts:
      - name: simulation-shared-nvme
        mountPath: /mnt/data

  - name: bundle-visualization-assets
    container:
      image: registry.spacex.corp/ndesim/export-util:v1.0
      command: [python3, /app/bundle_assets.py]
      volumeMounts:
      - name: simulation-shared-nvme
        mountPath: /mnt/data

```
Use code with caution.  
  
## 4. Data Integration & Production Mitigations  
Deploying automated physics pipelines on distributed clusters introduces strict infrastructure constraints. The platform addresses these challenges through targeted data integration layers. [++[1](https://startup.jobs/site-reliability-engineer-senior-or-staff-deployments-mongodb-8275944)++, ++[2](https://medium.com/@rudra910203/we-replaced-50-cronjobs-with-1-argo-workflow-was-it-worth-it-eedea2fe6f8f)++]  
## Resolving the Data Locality Problem  
High-resolution 3D simulation meshes can reach gigabytes in size. Transporting these large spatial datasets across distinct cluster nodes via virtualized network links degrades performance. [++[1](https://www.alphaxiv.org/abs/2603.24206)++, ++[2](https://akuity.io/blog/argo-101-what-is-argo)++]  
* *Mitigation:* The workflow utilizes shared, high-throughput **Kubernetes Persistent Volumes (PVs)** backed by local NVMe storage arrays. Tasks read and write matrix transformations directly to the shared local mount point (/mnt/data), eliminating network data transit overhead.  
## Preventing API Server Throttling  
When high-throughput NDE inspection scripts continuously invoke short-lived batch workflows simultaneously, the rapid creation and destruction of pods can flood and destabilize the core **Kubernetes API Server**. [++[1](https://medium.com/@rudra910203/we-replaced-50-cronjobs-with-1-argo-workflow-was-it-worth-it-eedea2fe6f8f)++]  
* *Mitigation:* Implement strict pod garbage collection policies (podGC) directly in the workflow spec and deploy the **Argo Emissary Executor** to route operational updates internally, minimizing overhead on the cluster control plane. [++[1](https://medium.com/@rudra910203/we-replaced-50-cronjobs-with-1-argo-workflow-was-it-worth-it-eedea2fe6f8f)++]  
## The Visualization Bridge  
Once an asynchronous Argo workflow completes, it compresses the resulting stress tensor arrays into a binary asset format and deposits it into an internal object storage bucket. The frontend dashboard fetches these pre-calculated matrices over standard HTTP blocks to display historical baselines instantly.  
## 5. Interview Pitch Presentation Outline  
A structured timeline designed for a 15-to-20 minute technical interview presentation with the NDE & Materials Software panel.  
* **Slide 1: Title & Objective**  
    * *Heading:* Real-Time Surrogate Accelerated Modeling of CMC Fracture Interfaces.  
    * *Talking Points:* Reorienting multiscale materials simulation around the demands of rapid vehicle reuse by pairing FNO engines with interactive web-based visualization platforms. [++[1](https://talents.vaia.com/companies/spacex/materials-engineer-lab-34203944/)++]  
* **Slide 2: The Core Challenge: Reusability Turnaround Bottlenecks**  
    * *Heading:* Post-Flight NDE Assessment Overhead.  
    * *Talking Points:* Traditional FEA mesh relaxation limits engineering velocity. Delamination and crack-front tracking for advanced ceramics require instant evaluation to avoid fleet groundings. [++[1](https://www.basenor.com/blogs/news/musk-declares-starship-heat-shield-problem-solved-after-flight-13)++, ++[2](https://www.facebook.com/groups/436711088832255/posts/915127854323907/)++]  
* **Slide 3: Proposed Architecture: Asynchronous Splitting**  
    * *Heading:* Decoupling Batch Pipelines from Live Tooling.  
    * *Talking Points:* Explaining how Argo Workflows acts as the scalable data engine to generate massive synthetic data or compile high-fidelity verification arrays on cluster environments, while client tools remain reactive. [++[1](https://www.alphaxiv.org/abs/2603.24206)++, ++[2](https://akuity.io/blog/argo-101-what-is-argo)++]  
* **Slide 4: Live Demo: Interactive Surrogate Canvas**  
    * *Heading:* Client-Side FNO Inference Visualization.  
    * *Talking Points:* Pivot directly to the browser view. Adjust the thermal and shear configuration sliders live, execute the FNO simulation instantly to observe immediate crack front deformations, and highlight the compute benchmark delta. [++[1](https://talents.vaia.com/companies/spacex/materials-engineer-lab-34203944/)++]  
* **Slide 5: Scaling up: Cluster Operations & Production Safety**  
    * *Heading:* Handling Storage Locality & API Protection on Kubernetes.  
    * *Talking Points:* Discussing shared NVMe persistent volume strategies to bypass data transit latencies and cluster optimization mechanics. [++[1](https://medium.com/@rudra910203/we-replaced-50-cronjobs-with-1-argo-workflow-was-it-worth-it-eedea2fe6f8f)++]  
* **Slide 6: Conclusion & QA**  
    * *Heading:* Engineering Velocity for Multi-Planetary Exploration.  
    * *Talking Points:* Reemphasizing the goal: empowering SpaceX structures engineers with fast, accessible spatial data analysis to build safer, rapidly reusable spaceflight hardware. [++[1](https://starship-spacex.fandom.com/wiki/Starship_Thermal_Protection_System_(TPS))++]  
  
  
  
  
  
**SpaceX Pitch: CMC Fracture Mechanics & Interface Surrogate Simulator**  
  
<!DOCTYPE html>  
<html lang="en">  
<head>  
    <meta charset="UTF-8">  
    <meta name="viewport" content="width=device-width, initial-scale=1.0">  
    <title>SpaceX NDE Simulation Pitch - Option C</title>  
    *<!-- Authoritative CDN for Three.js -->*  
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>  
    <style>  
        :root {  
            --bg-dark: #07080c;  
            --bg-panel: #0d111a;  
            --bg-card: #161b26;  
            --border-color: #242c3d;  
            --text-primary: #f0f4f8;  
            --text-secondary: #8a99ad;  
            --spacex-blue: #005288;  
            --accent-cyan: #00f0ff;  
            --accent-green: #39ff14;  
            --accent-orange: #ff9f00;  
            --danger-red: #ff3366;  
        }  
  
        * {  
            box-sizing: border-box;  
            margin: 0;  
            padding: 0;  
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;  
            -webkit-font-smoothing: antialiased;  
        }  
  
        body {  
            background-color: var(--bg-dark);  
            color: var(--text-primary);  
            overflow-x: hidden;  
            display: flex;  
            flex-direction: column;  
            min-height: 100vh;  
        }  
  
        header {  
            background-color: var(--bg-panel);  
            border-bottom: 1px solid var(--border-color);  
            padding: 1.25rem 2rem;  
            display: flex;  
            justify-content: space-between;  
            align-items: center;  
        }  
  
        .logo-area h1 {  
            font-size: 1.3rem;  
            font-weight: 700;  
            letter-spacing: 1.5px;  
            text-transform: uppercase;  
            background: linear-gradient(90deg, #fff, var(--accent-cyan));  
            -webkit-background-clip: text;  
            -webkit-text-fill-color: transparent;  
        }  
  
        .logo-area span {  
            font-size: 0.75rem;  
            color: var(--text-secondary);  
            display: block;  
            margin-top: 0.25rem;  
        }  
  
        .badge {  
            background: rgba(0, 240, 255, 0.1);  
            border: 1px solid var(--accent-cyan);  
            color: var(--accent-cyan);  
            padding: 0.3rem 0.8rem;  
            border-radius: 4px;  
            font-size: 0.75rem;  
            font-weight: 600;  
            letter-spacing: 0.5px;  
        }  
  
        .main-container {  
            display: flex;  
            flex: 1;  
            padding: 1.5rem;  
            gap: 1.5rem;  
            flex-wrap: wrap;  
        }  
  
        .control-panel {  
            flex: 1;  
            min-width: 340px;  
            max-width: 440px;  
            background-color: var(--bg-panel);  
            border: 1px solid var(--border-color);  
            border-radius: 8px;  
            padding: 1.5rem;  
            display: flex;  
            flex-direction: column;  
            gap: 1.5rem;  
        }  
  
        .visualization-panel {  
            flex: 2;  
            min-width: 500px;  
            background-color: var(--bg-panel);  
            border: 1px solid var(--border-color);  
            border-radius: 8px;  
            display: flex;  
            flex-direction: column;  
            position: relative;  
            min-height: 550px;  
        }  
  
        @media (max-width: 1024px) {  
            .visualization-panel {  
                min-width: 100%;  
            }  
            .control-panel {  
                max-width: 100%;  
            }  
        }  
  
        .section-title {  
            font-size: 0.85rem;  
            text-transform: uppercase;  
            letter-spacing: 1.2px;  
            color: var(--accent-cyan);  
            margin-bottom: 1rem;  
            border-bottom: 1px solid var(--border-color);  
            padding-bottom: 0.5rem;  
        }  
  
        .form-group {  
            margin-bottom: 1.25rem;  
        }  
  
        label {  
            display: flex;  
            justify-content: space-between;  
            font-size: 0.8rem;  
            color: var(--text-secondary);  
            margin-bottom: 0.5rem;  
        }  
  
        .range-value {  
            color: var(--text-primary);  
            font-weight: 600;  
        }  
  
        select, input[type="range"] {  
            width: 100%;  
            background-color: var(--bg-card);  
            border: 1px solid var(--border-color);  
            color: var(--text-primary);  
            padding: 0.65rem;  
            border-radius: 4px;  
            outline: none;  
        }  
  
        input[type="range"] {  
            padding: 0.2rem 0;  
            cursor: pointer;  
        }  
  
        select:focus {  
            border-color: var(--accent-cyan);  
        }  
  
        .btn-group {  
            display: grid;  
            grid-template-columns: 1fr 1fr;  
            gap: 1rem;  
            margin-top: 0.5rem;  
        }  
  
        button {  
            padding: 0.8rem 1rem;  
            border: none;  
            border-radius: 4px;  
            font-weight: 600;  
            cursor: pointer;  
            transition: all 0.2s ease;  
            text-transform: uppercase;  
            font-size: 0.75rem;  
            letter-spacing: 0.5px;  
        }  
  
        .btn-traditional {  
            background-color: var(--bg-card);  
            border: 1px solid var(--text-secondary);  
            color: var(--text-primary);  
        }  
  
        .btn-traditional:hover:not(:disabled) {  
            background-color: #242c3d;  
            border-color: #fff;  
        }  
  
        .btn-surrogate {  
            background-gradient: linear-gradient(135deg, var(--spacex-blue), var(--accent-cyan));  
            background-color: var(--spacex-blue);  
            color: white;  
            box-shadow: 0 4px 12px rgba(0, 82, 136, 0.3);  
            border: 1px solid rgba(0, 240, 255, 0.3);  
        }  
  
        .btn-surrogate:hover:not(:disabled) {  
            background-color: #0063a3;  
            border-color: var(--accent-cyan);  
            transform: translateY(-1px);  
        }  
  
        button:disabled {  
            opacity: 0.3;  
            cursor: not-allowed;  
            transform: none !important;  
        }  
  
        #canvas3d {  
            width: 100%;  
            flex: 1;  
            border-radius: 0 0 8px 8px;  
            background-color: #040508;  
        }  
  
        .viz-header {  
            padding: 1rem 1.25rem;  
            border-bottom: 1px solid var(--border-color);  
            display: flex;  
            justify-content: space-between;  
            align-items: center;  
            background-color: rgba(22, 27, 38, 0.4);  
        }  
  
        .telemetry-overlay {  
            position: absolute;  
            bottom: 1.5rem;  
            left: 1.5rem;  
            background: rgba(13, 17, 26, 0.9);  
            border: 1px solid var(--border-color);  
            padding: 1rem;  
            border-radius: 6px;  
            pointer-events: none;  
            display: flex;  
            flex-direction: column;  
            gap: 0.5rem;  
            font-family: 'Courier New', Courier, monospace;  
            font-size: 0.8rem;  
            min-width: 270px;  
            backdrop-filter: blur(6px);  
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);  
        }  
  
        .telemetry-row {  
            display: flex;  
            justify-content: space-between;  
        }  
  
        .telemetry-val {  
            color: var(--accent-cyan);  
            font-weight: bold;  
        }  
  
        .performance-card {  
            background-color: var(--bg-card);  
            border: 1px solid var(--border-color);  
            border-radius: 6px;  
            padding: 1.25rem;  
            margin-top: auto;  
        }  
  
        .perf-metric {  
            display: flex;  
            align-items: center;  
            justify-content: space-between;  
            margin-bottom: 0.4rem;  
        }  
  
        .perf-bar-container {  
            width: 100%;  
            height: 6px;  
            background-color: var(--bg-dark);  
            border-radius: 3px;  
            overflow: hidden;  
            margin-top: 0.25rem;  
            margin-bottom: 0.75rem;  
        }  
  
        .perf-bar {  
            height: 100%;  
            width: 0%;  
            transition: width 0.4s cubic-bezier(0.1, 0.8, 0.2, 1);  
        }  
  
        .progress-overlay {  
            position: absolute;  
            top: 0;  
            left: 0;  
            width: 100%;  
            height: 100%;  
            background: rgba(7, 8, 12, 0.85);  
            display: flex;  
            flex-direction: column;  
            justify-content: center;  
            align-items: center;  
            gap: 1.25rem;  
            z-index: 10;  
            opacity: 0;  
            pointer-events: none;  
            transition: opacity 0.3s ease;  
        }  
  
        .progress-overlay.active {  
            opacity: 1;  
            pointer-events: auto;  
        }  
  
        .spinner {  
            width: 45px;  
            height: 45px;  
            border: 3px solid var(--border-color);  
            border-top: 3px solid var(--accent-cyan);  
            border-radius: 50%;  
            animation: spin 0.8s linear infinite;  
        }  
  
        @keyframes spin {  
            0% { transform: rotate(0deg); }  
            100% { transform: rotate(360deg); }  
        }  
  
        .custom-message-box {  
            background-color: rgba(255, 159, 0, 0.12);  
            border: 1px solid var(--accent-orange);  
            color: var(--accent-orange);  
            padding: 0.75rem;  
            border-radius: 4px;  
            font-size: 0.78rem;  
            margin-bottom: 1rem;  
            display: none;  
            line-height: 1.3;  
        }  
    </style>  
</head>  
<body>  
  
    <header>  
        <div class="logo-area">  
            <h1>CMCFractureAI</h1>  
            <span>NDE & Materials Software Pitch • Option C Prototype</span>  
        </div>  
        <div class="badge">Fourier Neural Operator (FNO) Surrogate</div>  
    </header>  
  
    <div class="main-container">  
        *<!-- Control Panel Side -->*  
        <div class="control-panel">  
            <div>  
                <div class="section-title">Microstructural & Loading Bounds</div>  
                  
                <div class="form-group">  
                    <label for="materialArchitecture">Matrix Architecture</label>  
                    <select id="materialArchitecture">  
                        <option value="sic_sic">SiC/SiC Continuous Fiber Composite</option>  
                        <option value="c_sic">C/SiC High-Thermal Composite</option>  
                        <option value="layered_tufroc">Layered Fibrous Insulation (TUFROC Derivative)</option>  
                    </select>  
                </div>  
  
                <div class="form-group">  
                    <label for="thermalGradient">Thermal Gradient (°C/mm) <span class="range-value" id="thermalGradientCurrent">120</span></label>  
                    <input type="range" id="thermalGradient" min="20" max="250" step="10" value="120">  
                </div>  
  
                <div class="form-group">  
                    <label for="mechanicalLoad">Aerodynamic Shear Load (kN) <span class="range-value" id="mechanicalLoadCurrent">45</span></label>  
                    <input type="range" id="mechanicalLoad" min="5" max="100" step="5" value="45">  
                </div>  
  
                <div class="form-group">  
                    <label for="coatingStrength">Fiber Coating Shear Limit (MPa) <span class="range-value" id="coatingStrengthCurrent">60</span></label>  
                    <input type="range" id="coatingStrength" min="10" max="150" step="5" value="60">  
                </div>  
            </div>  
  
            <div>  
                <div class="section-title">Solver Architecture</div>  
                <div id="customAlert" class="custom-message-box"></div>  
                  
                <div class="btn-group">  
                    <button class="btn-traditional" id="btnRunFEA">Run Finite Element</button>  
                    <button class="btn-surrogate" id="btnRunFNO">Run FNO AI</button>  
                </div>  
            </div>  
  
            <div class="performance-card">  
                <div class="section-title" style="font-size:0.75rem; margin-bottom:0.6rem; border-bottom: none; padding-bottom:0;">Solver Evaluation Compute Overhead</div>  
                  
                <div class="perf-metric">  
                    <span style="font-size:0.75rem; color: var(--text-secondary);">Traditional FEM Mesh Solver</span>  
                    <span id="feaTimeText" style="font-size:0.75rem; font-weight:bold; color: var(--danger-red);">--</span>  
                </div>  
                <div class="perf-bar-container">  
                    <div id="feaBar" class="perf-bar" style="background-color: var(--danger-red);"></div>  
                </div>  
                  
                <div class="perf-metric">  
                    <span style="font-size:0.75rem; color: var(--text-secondary);">Neural Operator Surrogate</span>  
                    <span id="fnoTimeText" style="font-size:0.75rem; font-weight:bold; color: var(--accent-green);">--</span>  
                </div>  
                <div class="perf-bar-container">  
                    <div id="fnoBar" class="perf-bar" style="background-color: var(--accent-green);"></div>  
                </div>  
            </div>  
        </div>  
  
        *<!-- Visualization Side -->*  
        <div class="visualization-panel">  
            <div class="progress-overlay" id="loadingOverlay">  
                <div class="spinner"></div>  
                <div id="progressText" style="font-weight: 600; font-size: 0.85rem; letter-spacing: 0.5px;">Initializing Microstructure Mesh...</div>  
            </div>  
              
            <div class="viz-header">  
                <div style="font-size: 0.85rem; font-weight: 600; letter-spacing: 0.3px;" id="vizTitle">Status: System Idle</div>  
                <div style="font-size: 0.75rem; color: var(--text-secondary);" id="engineMode">Visualizing: Material Continuum</div>  
            </div>  
              
            *<!-- Three.js Container -->*  
            <div id="canvas3d"></div>  
  
            *<!-- NDE Telemetry Data Overlay -->*  
            <div class="telemetry-overlay">  
                <div class="telemetry-row">  
                    <span>Micro-FE Nodes:</span>  
                    <span class="telemetry-val" id="telNodes">640,000</span>  
                </div>  
                <div class="telemetry-row">  
                    <span>Max Energy Release (G_Ic):</span>  
                    <span class="telemetry-val" id="telEnergy">0.00 J/m²</span>  
                </div>  
                <div class="telemetry-row">  
                    <span>Delamination Area:</span>  
                    <span class="telemetry-val" id="telArea">0.00 mm²</span>  
                </div>  
                <div class="telemetry-row">  
                    <span>Structural Margins:</span>  
                    <span class="telemetry-val" id="telMargin" style="color: var(--accent-green);">+0.00 (Nominal)</span>  
                </div>  
            </div>  
        </div>  
    </div>  
  
    <script>  
        // --- Core Application State ---  
        let scene, camera, renderer, compositeGroup, matrixBlock;  
        let fibersArray = [];  
        let crackPlaneMesh;  
        let animationFrameId;  
        let isSimulating = false;  
        let simProgress = 0;  
        let currentSolver = 'FNO';  
  
        // Operational constraints configured via control panel inputs  
        const inputs = {  
            architecture: 'sic_sic',  
            thermalGradient: 120,  
            mechanicalLoad: 45,  
            coatingStrength: 60  
        };  
  
        // DOM Element Registration  
        const thermalGradientSlider = document.getElementById('thermalGradient');  
        const thermalGradientCurrent = document.getElementById('thermalGradientCurrent');  
        const mechanicalLoadSlider = document.getElementById('mechanicalLoad');  
        const mechanicalLoadCurrent = document.getElementById('mechanicalLoadCurrent');  
        const coatingStrengthSlider = document.getElementById('coatingStrength');  
        const coatingStrengthCurrent = document.getElementById('coatingStrengthCurrent');  
        const archSelect = document.getElementById('materialArchitecture');  
        const btnRunFEA = document.getElementById('btnRunFEA');  
        const btnRunFNO = document.getElementById('btnRunFNO');  
        const vizTitle = document.getElementById('vizTitle');  
        const engineMode = document.getElementById('engineMode');  
        const loadingOverlay = document.getElementById('loadingOverlay');  
        const progressText = document.getElementById('progressText');  
        const customAlert = document.getElementById('customAlert');  
  
        // Telemetry DOM elements  
        const telNodes = document.getElementById('telNodes');  
        const telEnergy = document.getElementById('telEnergy');  
        const telArea = document.getElementById('telArea');  
        const telMargin = document.getElementById('telMargin');  
  
        // Performance DOM elements  
        const feaTimeText = document.getElementById('feaTimeText');  
        const fnoTimeText = document.getElementById('fnoTimeText');  
        const feaBar = document.getElementById('feaBar');  
        const fnoBar = document.getElementById('fnoBar');  
  
        // --- Event Listeners and Input Synchronizers ---  
        thermalGradientSlider.addEventListener('input', (e) => {  
            thermalGradientCurrent.innerText = e.target.value;  
            inputs.thermalGradient = parseInt(e.target.value);  
        });  
  
        mechanicalLoadSlider.addEventListener('input', (e) => {  
            mechanicalLoadCurrent.innerText = e.target.value;  
            inputs.mechanicalLoad = parseInt(e.target.value);  
        });  
  
        coatingStrengthSlider.addEventListener('input', (e) => {  
            coatingStrengthCurrent.innerText = e.target.value;  
            inputs.coatingStrength = parseInt(e.target.value);  
        });  
  
        archSelect.addEventListener('change', (e) => {  
            inputs.architecture = e.target.value;  
            generateMicrostructure(e.target.value);  
        });  
  
        btnRunFEA.addEventListener('click', () => dispatchSimulation('FEA'));  
        btnRunFNO.addEventListener('click', () => dispatchSimulation('FNO'));  
  
        function displayAlert(msg) {  
            customAlert.innerText = msg;  
            customAlert.style.display = 'block';  
            setTimeout(() => { customAlert.style.display = 'none'; }, 4500);  
        }  
  
        // --- Three.js Microstructural Setup Engine ---  
        function initCompositeViewer() {  
            const container = document.getElementById('canvas3d');  
              
            scene = new THREE.Scene();  
            scene.background = new THREE.Color(0x040508);  
  
            camera = new THREE.PerspectiveCamera(40, container.clientWidth / container.clientHeight, 0.1, 1000);  
            camera.position.set(5, 4, 7);  
            camera.lookAt(0, 0, 0);  
  
            renderer = new THREE.WebGLRenderer({ antialias: true });  
            renderer.setSize(container.clientWidth, container.clientHeight);  
            container.appendChild(renderer.domElement);  
  
            // Lighting orchestration to isolate structural geometries  
            const ambient = new THREE.AmbientLight(0xffffff, 0.3);  
            scene.add(ambient);  
  
            const spot1 = new THREE.SpotLight(0xffffff, 1.5);  
            spot1.position.set(10, 15, 10);  
            scene.add(spot1);  
  
            const neonDrive = new THREE.DirectionalLight(0x00f0ff, 0.8);  
            neonDrive.position.set(-10, -5, -5);  
            scene.add(neonDrive);  
  
            // Structure root organizational group  
            compositeGroup = new THREE.Group();  
            scene.add(compositeGroup);  
  
            generateMicrostructure('sic_sic');  
  
            window.addEventListener('resize', onResizeHandler);  
            renderLoop();  
        }  
  
        // Procedural generator illustrating woven ceramic architectures and coatings  
        function generateMicrostructure(archType) {  
            // Flush group parameters  
            while(compositeGroup.children.length > 0){   
                compositeGroup.remove(compositeGroup.children[0]);   
            }  
            fibersArray = [];  
  
            let matrixColor, fiberColor, nodeCount;  
            if (archType === 'sic_sic') {  
                matrixColor = 0x222630;  
                fiberColor = 0x48536b;  
                nodeCount = "640,000";  
            } else if (archType === 'c_sic') {  
                matrixColor = 0x181b21;  
                fiberColor = 0x2d313b;  
                nodeCount = "895,000";  
            } else {  
                matrixColor = 0x3d3530;  
                fiberColor = 0x736760;  
                nodeCount = "310,000";  
            }  
            telNodes.innerText = nodeCount;  
  
            // Generate representative continuum block matrix representation  
            const matrixGeo = new THREE.BoxGeometry(3, 2, 2);  
            const matrixMat = new THREE.MeshStandardMaterial({  
                color: matrixColor,  
                roughness: 0.6,  
                metalness: 0.1,  
                transparent: true,  
                opacity: 0.65,  
                wireframe: false  
            });  
            matrixBlock = new THREE.Mesh(matrixGeo, matrixMat);  
            compositeGroup.add(matrixBlock);  
  
            // Generate reinforcing ceramic structural fibers embedded along the load path  
            const fiberGeo = new THREE.CylinderGeometry(0.12, 0.12, 3, 16);  
            fiberGeo.rotateZ(Math.PI / 2); // Align parallel to loading vector  
  
            const fiberOffsets = [  
                {y: 0.4, z: 0.4}, {y: 0.4, z: -0.4},  
                {y: -0.4, z: 0.4}, {y: -0.4, z: -0.4},  
                {y: 0, z: 0.6}, {y: 0, z: -0.6}  
            ];  
  
            fiberOffsets.forEach(offset => {  
                // Outer fiber representing the interface coating profile (hex-BN boundary layer)  
                const coatingGeo = new THREE.CylinderGeometry(0.15, 0.15, 3, 16);  
                coatingGeo.rotateZ(Math.PI / 2);  
                const coatingMat = new THREE.MeshStandardMaterial({  
                    color: 0x00f0ff,  
                    transparent: true,  
                    opacity: 0.15,  
                    wireframe: true  
                });  
                const coatingMesh = new THREE.Mesh(coatingGeo, coatingMat);  
                coatingMesh.position.set(0, offset.y, offset.z);  
                compositeGroup.add(coatingMesh);  
  
                // Core Fiber mesh  
                const fiberMat = new THREE.MeshStandardMaterial({  
                    color: fiberColor,  
                    roughness: 0.4,  
                    metalness: 0.3  
                });  
                const fiberMesh = new THREE.Mesh(fiberGeo, fiberMat);  
                fiberMesh.position.set(0, offset.y, offset.z);  
                compositeGroup.add(fiberMesh);  
                fibersArray.push(fiberMesh);  
            });  
  
            // Initialize structural micro-crack nucleus geometry   
            const crackGeo = new THREE.PlaneGeometry(0.1, 1.6);  
            crackGeo.rotateY(Math.PI / 2);  
            const crackMat = new THREE.MeshBasicMaterial({  
                color: 0xff3366,  
                side: THREE.DoubleSide,  
                transparent: true,  
                opacity: 0.9  
            });  
            crackPlaneMesh = new THREE.Mesh(crackGeo, crackMat);  
            // Locate nucleus at the left boundary of matrix  
            crackPlaneMesh.position.set(-1.49, 0, 0);  
            compositeGroup.add(crackPlaneMesh);  
        }  
  
        function onResizeHandler() {  
            const container = document.getElementById('canvas3d');  
            camera.aspect = container.clientWidth / container.clientHeight;  
            camera.updateProjectionMatrix();  
            renderer.setSize(container.clientWidth, container.clientHeight);  
        }  
  
        function renderLoop() {  
            animationFrameId = requestAnimationFrame(renderLoop);  
              
            // Auto rotate view to capture micro-crack propagation profiling fields  
            if (compositeGroup) {  
                compositeGroup.rotation.y = Math.sin(Date.now() * 0.0003) * 0.4 + 0.3;  
                compositeGroup.rotation.x = 0.25;  
            }  
  
            if (isSimulating) {  
                stepFractureKinetics();  
            }  
  
            renderer.render(scene, camera);  
        }  
  
        // --- Simulation Dispatch Mechanics ---  
        function dispatchSimulation(solverType) {  
            if (isSimulating) return;  
  
            currentSolver = solverType;  
            simProgress = 0;  
  
            if (solverType === 'FEA') {  
                // Simulate multi-pass matrix relaxation delay  
                loadingOverlay.classList.add('active');  
                btnRunFEA.disabled = true;  
                btnRunFNO.disabled = true;  
  
                let stateIndex = 0;  
                const logs = [  
                    "Constructing Global Stiffness Matrix...",  
                    "Solving Multiscale Displacement Fields...",  
                    "Computing Energy Release Rate Vectors...",  
                    "Evaluating J-Integral Fracture Vectors..."  
                ];  
  
                const loggerTimer = setInterval(() => {  
                    progressText.innerText = logs[stateIndex];  
                    stateIndex++;  
                    if (stateIndex >= logs.length) {  
                        clearInterval(loggerTimer);  
                        loadingOverlay.classList.remove('active');  
                        igniteVisualizationTrack(6.42); // Traditional multi-second cost  
                    }  
                }, 1100);  
  
            } else {  
                // Fourier Neural Operator maps boundary layers continuously in 1 frame  
                igniteVisualizationTrack(0.005);  
            }  
        }  
  
        function igniteVisualizationTrack(durationSeconds) {  
            isSimulating = true;  
            vizTitle.innerText = `Status: Processing ${currentSolver} Evaluation`;  
            engineMode.innerText = "Visualizing: Von Mises Stress Matrix Field";  
  
            if (currentSolver === 'FEA') {  
                feaTimeText.innerText = `${durationSeconds} s`;  
                feaBar.style.width = '100%';  
            } else {  
                fnoTimeText.innerText = `${durationSeconds} s`;  
                fnoBar.style.width = '1.2%'; // Microbar representing lightning-fast calculation  
            }  
  
            btnRunFEA.disabled = true;  
            btnRunFNO.disabled = true;  
        }  
  
        function stepFractureKinetics() {  
            simProgress += 0.012; // Controls continuous propagation velocity animation  
  
            if (simProgress >= 1.0) {  
                isSimulating = false;  
                simProgress = 1.0;  
                vizTitle.innerText = "Status: Analysis Complete";  
                engineMode.innerText = "Visualizing: Post-Flight Structural Continuum";  
                btnRunFEA.disabled = false;  
                btnRunFNO.disabled = false;  
                  
                // Final safety margin check  
                const endMargin = parseFloat(telMargin.innerText);  
                if (endMargin < 0) {  
                    displayAlert("CRITICAL: Structural margin limits violated. Delamination front propagation exceeds safety envelope.");  
                } else {  
                    displayAlert("CRITICAL: Evaluation Complete. Interfacial coatings managed pseudo-ductile crack arresting thresholds.");  
                }  
                return;  
            }  
  
            // Calculations leveraging inputs to morph fracture mechanics parameters dynamically  
            const loadFactor = inputs.mechanicalLoad / 45;  
            const thermalFactor = inputs.thermalGradient / 120;  
            const coatingResistance = inputs.coatingStrength / 60;  
  
            // Crack propagation distance relies directly on thermomechanical limits vs fiber coating interface bounds  
            const finalExtentX = 2.8 * (loadFactor * thermalFactor) / coatingResistance;  
            const activeScaleX = simProgress * Math.min(finalExtentX, 2.9);  
  
            // Re-scale the 3D plane mesh visualization to demonstrate propagation vectors  
            crackPlaneMesh.scale.x = activeScaleX * 10;   
            crackPlaneMesh.position.x = -1.49 + (activeScaleX / 2);  
  
            // Telemetry calculations structured via Data Integrity protocols  
            const calculatedEnergyRelease = (loadFactor * thermalFactor * 180) * simProgress;  
            telEnergy.innerText = `${calculatedEnergyRelease.toFixed(1)} J/m²`;  
  
            const estimatedDelamArea = (activeScaleX * 1.6 * 12.5);  
            telArea.innerText = `${estimatedDelamArea.toFixed(2)} mm²`;  
  
            const safetyMargin = (coatingResistance * 1.5) - (loadFactor * thermalFactor * simProgress * 1.4);  
            telMargin.innerText = `${safetyMargin.toFixed(2)}`;  
              
            if (safetyMargin < 0) {  
                telMargin.style.color = 'var(--danger-red)';  
            } else if (safetyMargin < 0.3) {  
                telMargin.style.color = 'var(--accent-orange)';  
            } else {  
                telMargin.style.color = 'var(--accent-green)';  
            }  
  
            // High Von Mises stress fields representation: shift matrix material properties into a highly stressed neon shade  
            if (matrixBlock) {  
                const thermalIntensity = Math.min(inputs.thermalGradient / 250, 1.0);  
                matrixBlock.material.color.setRGB(  
                    0.13 + (simProgress * 0.4 * thermalIntensity),   
                    0.15 - (simProgress * 0.1),   
                    0.20 + (simProgress * 0.2 * (1 - thermalIntensity))  
                );  
            }  
        }  
  
        // Initialize viewport orchestration on standard load track  
        window.onload = function() {  
            initCompositeViewer();  
        };  
    </script>  
</body>  
</html>  
  
  
  
  
  
