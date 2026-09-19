import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

const COLORS = {
  thinking: '#00f0ff', // Processing
  waiting:  '#ffaa00', // Awaiting I/O
  stuck:    '#ff0055', // Blocked
  finished: '#00ffaa', // Sequence Complete
  blast:    '#ff0055', // Hazard red for the cascade
  dim:      '#1a2230', // Everything outside the radius of effect
};

const NUM_AGENTS = 24;

const generateTopology = () => {
  const nodes = [];
  const edges = [];
  const radius = 35;

  // Generate Agents in a 3D spherical cluster
  for (let i = 0; i < NUM_AGENTS; i++) {
    const phi = Math.acos(-1 + (2 * i) / NUM_AGENTS);
    const theta = Math.sqrt(NUM_AGENTS * Math.PI) * phi;
    
    // Add organic noise to positions
    const r = radius + (Math.random() * 15 - 7.5);
    
    nodes.push({
      id: `AG-${1000 + i}`,
      position: new THREE.Vector3(
        r * Math.cos(theta) * Math.sin(phi),
        r * Math.sin(theta) * Math.sin(phi),
        r * Math.cos(phi)
      ),
      // Weighted random states for visual variation
      state: Math.random() > 0.8 ? 'stuck' : Math.random() > 0.6 ? 'waiting' : Math.random() > 0.8 ? 'finished' : 'thinking',
      workload: Math.random() * 100,
      connections: [],
      // Properties assigned later by the engine
      group: null,
      materials: {}
    });
  }

  // Generate Network Edges
  nodes.forEach((node, i) => {
    const distances = nodes
      .map((n, idx) => ({ idx, dist: node.position.distanceTo(n.position) }))
      .filter(n => n.idx !== i)
      .sort((a, b) => a.dist - b.dist);

    const numConnections = Math.floor(Math.random() * 3) + 1;
    for (let j = 0; j < numConnections; j++) {
      const targetIdx = distances[j].idx;
      if (!node.connections.includes(targetIdx)) {
        node.connections.push(targetIdx);
        edges.push({ source: i, target: targetIdx });
      }
    }
  });

  return { nodes, edges };
};

export default function FleetReactorApp() {
  const mountRef = useRef(null);
  const radialMenuRef = useRef(null);
  const tooltipRef = useRef(null);
  
  // React State for UI rendering
  const [uiState, setUiState] = useState({
    selectedNodeId: null,
    hoveredNodeId: null,
    blastMode: false
  });

  // Mutable app state for the Three.js loop (avoids stale closures and re-renders)
  const engineState = useRef({
    selectedNode: null,
    hoveredNode: null,
    blastMode: false,
    nodes: [],
    edges: [],
    particles: []
  });

  // Ensure Tailwind is loaded in standard environments if missing
  useEffect(() => {
    if (!document.getElementById('tailwind-script')) {
      const script = document.createElement('script');
      script.id = 'tailwind-script';
      script.src = 'https://cdn.tailwindcss.com';
      document.head.appendChild(script);
    }
  }, []);

  useEffect(() => {
    if (!mountRef.current) return;

    // --- 1. Scene Setup ---
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2('#030508', 0.008);
    
    const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor('#030508');
    mountRef.current.appendChild(renderer.domElement);

    // --- 2. Data Initialization ---
    const topology = generateTopology();
    const mainGroup = new THREE.Group();
    scene.add(mainGroup);

    // Reusable Geometries
    const coreGeo = new THREE.IcosahedronGeometry(1.2, 1);
    const glowGeo = new THREE.SphereGeometry(2.5, 32, 32);
    const ringGeo = new THREE.TorusGeometry(3.5, 0.05, 16, 64);

    // --- 3. Build Nodes ---
    topology.nodes.forEach((node) => {
      const group = new THREE.Group();
      group.position.copy(node.position);
      
      const baseColor = new THREE.Color(COLORS[node.state]);
      
      // Core Wireframe
      const coreMat = new THREE.MeshBasicMaterial({ color: baseColor, wireframe: true, transparent: true, opacity: 0.8 });
      const core = new THREE.Mesh(coreGeo, coreMat);
      
      // Volumetric Glow (Additive Blending)
      const glowMat = new THREE.MeshBasicMaterial({ 
        color: baseColor, 
        transparent: true, 
        opacity: 0.15, 
        blending: THREE.AdditiveBlending,
        depthWrite: false 
      });
      const glow = new THREE.Mesh(glowGeo, glowMat);
      
      // Orbital Tech Ring
      const ringMat = new THREE.MeshBasicMaterial({ 
        color: baseColor, 
        transparent: true, 
        opacity: 0.4, 
        blending: THREE.AdditiveBlending,
        depthWrite: false 
      });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      
      // Randomize ring starting rotation
      ring.rotation.x = Math.random() * Math.PI;
      ring.rotation.y = Math.random() * Math.PI;

      group.add(core);
      group.add(glow);
      group.add(ring);
      
      // Scale based on workload
      const scale = 0.5 + (node.workload / 100) * 0.7;
      group.scale.set(scale, scale, scale);

      mainGroup.add(group);
      
      // Store references in our engine state
      node.group = group;
      node.elements = { core, glow, ring };
      node.materials = { coreMat, glowMat, ringMat };
      node.baseScale = scale;
      node.baseColor = baseColor;
      
      engineState.current.nodes.push(node);
    });

    // --- 4. Build Edges & Data Particles ---
    const lineMat = new THREE.LineBasicMaterial({ color: '#334455', transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending });
    
    topology.edges.forEach((edgeData) => {
      const source = engineState.current.nodes[edgeData.source];
      const target = engineState.current.nodes[edgeData.target];
      
      const points = [source.position, target.position];
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geo, lineMat.clone()); // Clone so we can change colors individually later
      mainGroup.add(line);
      
      edgeData.line = line;
      edgeData.sourceNode = source;
      edgeData.targetNode = target;
      engineState.current.edges.push(edgeData);

      // Create a data particle for this edge
      const particleMat = new THREE.MeshBasicMaterial({ 
        color: source.baseColor, 
        transparent: true, 
        opacity: 0.8,
        blending: THREE.AdditiveBlending
      });
      const particle = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 8), particleMat);
      mainGroup.add(particle);
      
      engineState.current.particles.push({
        mesh: particle,
        edge: edgeData,
        progress: Math.random(),
        speed: 0.002 + Math.random() * 0.005
      });
    });

    // Ambient space dust
    const dustGeo = new THREE.BufferGeometry();
    const dustCount = 1000;
    const dustPos = new Float32Array(dustCount * 3);
    for(let i=0; i<dustCount*3; i++) dustPos[i] = (Math.random() - 0.5) * 200;
    dustGeo.setAttribute('position', new THREE.BufferAttribute(dustPos, 3));
    const dustMat = new THREE.PointsMaterial({ color: '#ffffff', size: 0.3, transparent: true, opacity: 0.2 });
    const dust = new THREE.Points(dustGeo, dustMat);
    scene.add(dust);

    // --- 5. Interaction Setup ---
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2(-1000, -1000); // start offscreen
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    
    // Camera Animation State
    const lookAtTarget = new THREE.Vector3(0, 0, 0);
    let orbitAngle = 0;

    const onPointerMove = (event) => {
      if (isDragging && !engineState.current.selectedNode) {
        const deltaX = event.clientX - previousMousePosition.x;
        orbitAngle -= deltaX * 0.005;
      }
      previousMousePosition = { x: event.clientX, y: event.clientY };

      mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    };

    const onPointerDown = () => { isDragging = true; };
    
    const onPointerUp = () => { 
      isDragging = false; 
      
      // Handle Click Selection
      if (engineState.current.hoveredNode) {
        engineState.current.selectedNode = engineState.current.hoveredNode;
        setUiState(prev => ({ ...prev, selectedNodeId: engineState.current.hoveredNode.id }));
      } else {
        // Clicked empty space
        engineState.current.selectedNode = null;
        engineState.current.blastMode = false;
        setUiState(prev => ({ ...prev, selectedNodeId: null, blastMode: false }));
      }
    };

    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointerup', onPointerUp);
    
    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };
    window.addEventListener('resize', onResize);

    // --- 6. Render Loop ---
    let reqId;
    const clock = new THREE.Clock();

    const animate = () => {
      reqId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Raycasting for Hover state (only if not drilled down)
      if (!engineState.current.selectedNode) {
        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(engineState.current.nodes.map(n => n.elements.glow));
        
        let foundHover = null;
        if (intersects.length > 0) {
          const hitMesh = intersects[0].object;
          foundHover = engineState.current.nodes.find(n => n.elements.glow === hitMesh);
        }

        if (foundHover !== engineState.current.hoveredNode) {
          // Reset old hover
          if (engineState.current.hoveredNode) {
             const old = engineState.current.hoveredNode;
             old.group.scale.set(old.baseScale, old.baseScale, old.baseScale);
             document.body.style.cursor = 'default';
          }
          // Set new hover
          if (foundHover) {
             foundHover.group.scale.set(foundHover.baseScale * 1.3, foundHover.baseScale * 1.3, foundHover.baseScale * 1.3);
             document.body.style.cursor = 'pointer';
             
             // Update Tooltip DOM natively for performance
             if(tooltipRef.current) {
               tooltipRef.current.style.opacity = '1';
               tooltipRef.current.style.left = `${(mouse.x * 0.5 + 0.5) * window.innerWidth + 20}px`;
               tooltipRef.current.style.top = `${-(mouse.y * 0.5 - 0.5) * window.innerHeight + 20}px`;
               document.getElementById('tt-id').innerText = foundHover.id;
               document.getElementById('tt-state').innerText = foundHover.state.toUpperCase();
               document.getElementById('tt-state').style.color = COLORS[foundHover.state];
             }
          } else {
             if(tooltipRef.current) tooltipRef.current.style.opacity = '0';
          }
          engineState.current.hoveredNode = foundHover;
        }
      } else {
        if(tooltipRef.current) tooltipRef.current.style.opacity = '0';
      }

      // Node Animations & Blast Radius Logic
      const selected = engineState.current.selectedNode;
      const blastOn = engineState.current.blastMode;
      
      // Pre-calculate blast targets if active
      let blastNodes = [];
      if (selected && blastOn) {
        blastNodes.push(selected.id);
        engineState.current.edges.forEach(e => {
          if (e.sourceNode.id === selected.id) blastNodes.push(e.targetNode.id);
          if (e.targetNode.id === selected.id) blastNodes.push(e.sourceNode.id);
        });
      }

      engineState.current.nodes.forEach(node => {
        // Gentle float
        node.group.position.y = node.position.y + Math.sin(time * 2 + node.position.x) * 0.5;
        // Ring spin
        node.elements.ring.rotation.x += delta * 0.5;
        node.elements.ring.rotation.y += delta * 0.3;

        // Visual states based on Blast Mode & Selection
        if (selected) {
           if (blastOn) {
             if (blastNodes.includes(node.id)) {
               // In blast radius
               const c = new THREE.Color(node.id === selected.id ? COLORS.blast : COLORS.waiting);
               node.materials.coreMat.color = c;
               node.materials.glowMat.color = c;
               node.materials.ringMat.color = c;
               node.materials.glowMat.opacity = 0.3;
             } else {
               // Dimmed
               const dim = new THREE.Color(COLORS.dim);
               node.materials.coreMat.color = dim;
               node.materials.glowMat.color = dim;
               node.materials.ringMat.color = dim;
               node.materials.glowMat.opacity = 0.05;
             }
           } else {
             // Selected but no blast (dim non-selected slightly)
             const targetOpacity = node.id === selected.id ? 0.3 : 0.05;
             node.materials.glowMat.opacity = THREE.MathUtils.lerp(node.materials.glowMat.opacity, targetOpacity, 0.1);
             // Restore colors
             node.materials.coreMat.color = node.baseColor;
             node.materials.glowMat.color = node.baseColor;
             node.materials.ringMat.color = node.baseColor;
           }
        } else {
           // Normal state
           node.materials.coreMat.color = node.baseColor;
           node.materials.glowMat.color = node.baseColor;
           node.materials.ringMat.color = node.baseColor;
           node.materials.glowMat.opacity = THREE.MathUtils.lerp(node.materials.glowMat.opacity, 0.15, 0.1);
        }
      });

      // Edge & Particle Updates
      engineState.current.edges.forEach(edge => {
        // Style lines based on blast mode
        if (selected && blastOn) {
          if (blastNodes.includes(edge.sourceNode.id) && blastNodes.includes(edge.targetNode.id)) {
            edge.line.material.color = new THREE.Color(COLORS.blast);
            edge.line.material.opacity = 0.8;
          } else {
            edge.line.material.color = new THREE.Color(COLORS.dim);
            edge.line.material.opacity = 0.1;
          }
        } else {
          edge.line.material.color = new THREE.Color('#334455');
          edge.line.material.opacity = 0.2;
        }
      });

      engineState.current.particles.forEach(p => {
        p.progress += p.speed;
        if (p.progress > 1) p.progress = 0;
        
        // Lerp position along the edge
        p.mesh.position.lerpVectors(p.edge.sourceNode.group.position, p.edge.targetNode.group.position, p.progress);
        
        // Hide particles if dimmed by blast radius
        if (selected && blastOn && !(blastNodes.includes(p.edge.sourceNode.id) && blastNodes.includes(p.edge.targetNode.id))) {
           p.mesh.material.opacity = 0;
        } else {
           p.mesh.material.opacity = 0.8;
        }
      });

      // Camera Rig Logic
      if (selected) {
        // Drill down to selected node
        const targetPos = selected.position.clone();
        const direction = targetPos.clone().normalize();
        
        // Calculate an offset position for the camera to look AT the node
        const offsetPos = targetPos.clone().add(direction.multiplyScalar(25));
        
        // Push slightly up for better angle
        offsetPos.y += 10;
        
        camera.position.lerp(offsetPos, 0.05);
        lookAtTarget.lerp(targetPos, 0.05);
        camera.lookAt(lookAtTarget);

        // Project Radial Menu 3D to 2D
        if (radialMenuRef.current) {
          const vector = targetPos.clone();
          vector.project(camera);
          
          const x = (vector.x * 0.5 + 0.5) * window.innerWidth;
          const y = -(vector.y * 0.5 - 0.5) * window.innerHeight;
          
          radialMenuRef.current.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;
          radialMenuRef.current.style.opacity = '1';
          radialMenuRef.current.style.pointerEvents = 'auto';
        }
      } else {
        // Global Orbit
        if (!isDragging) orbitAngle += 0.001;
        const radius = 90;
        const targetCamPos = new THREE.Vector3(Math.cos(orbitAngle) * radius, 30, Math.sin(orbitAngle) * radius);
        
        camera.position.lerp(targetCamPos, 0.05);
        lookAtTarget.lerp(new THREE.Vector3(0, 0, 0), 0.05);
        camera.lookAt(lookAtTarget);

        if (radialMenuRef.current) {
          radialMenuRef.current.style.opacity = '0';
          radialMenuRef.current.style.pointerEvents = 'none';
        }
      }

      renderer.render(scene, camera);
    };

    animate();

    // --- 7. Cleanup ---
    return () => {
      cancelAnimationFrame(reqId);
      window.removeEventListener('pointermove', onPointerMove);
      window.removeEventListener('pointerdown', onPointerDown);
      window.removeEventListener('pointerup', onPointerUp);
      window.removeEventListener('resize', onResize);
      if (mountRef.current) mountRef.current.removeChild(renderer.domElement);
      scene.clear();
    };
  }, []); // Run once on mount

  // Sync blast mode to engine ref when UI button clicked
  const toggleBlast = () => {
    const newMode = !uiState.blastMode;
    setUiState(prev => ({ ...prev, blastMode: newMode }));
    engineState.current.blastMode = newMode;
  };

  // --- LIVE TELEMETRY & ACTION SEAM ---
  // 1. Data Ingestion: Drop your Backstage WebSocket/REST fetch here.
  useEffect(() => {
    const pollTelemetry = async () => {
      try {
        // Uncomment and route to your live backend endpoint:
        // const res = await fetch('/api/fleet/status');
        // const liveNodes = await res.json();
        // ... map your live stats securely into engineState.current.nodes
      } catch (e) {
        console.error('Telemetry offline', e);
      }
    };
    const interval = setInterval(pollTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  // 2. Action Handlers: Dispatches actions back to your fleet controllers.
  const handleAction = (action) => {
    if (!uiState.selectedNodeId) return;
    console.log(`[COMMAND] Executing ${action} on agent ${uiState.selectedNodeId}`);
    
    // Optimistic 3D Engine Update (Instant visual feedback)
    const node = engineState.current.nodes.find(n => n.id === uiState.selectedNodeId);
    if (node) {
      if (action === 'stop') node.state = 'stuck';
      if (action === 'apprv') node.state = 'thinking';
      node.baseColor = new THREE.Color(COLORS[node.state]);
    }
  };

  return (
    <div className="w-full h-screen bg-[#030508] overflow-hidden text-white font-sans relative selection:bg-cyan-500/30">
      
      {/* 3D Canvas Mount Point */}
      <div ref={mountRef} className="absolute inset-0 cursor-crosshair"></div>

      {/* Hover Tooltip (Native DOM updated in Render Loop) */}
      <div 
        ref={tooltipRef} 
        className="absolute z-50 pointer-events-none opacity-0 transition-opacity duration-200 bg-black/60 backdrop-blur-md border border-white/10 p-3 rounded-lg flex flex-col gap-1 shadow-2xl"
      >
        <div className="text-[9px] uppercase tracking-widest text-white/40 font-mono">Node Identity</div>
        <div id="tt-id" className="text-sm font-bold font-mono text-white">---</div>
        <div id="tt-state" className="text-[10px] font-bold uppercase tracking-wider mt-1">---</div>
      </div>

      {/* Top HUD */}
      <div className="absolute top-0 left-0 w-full p-6 flex justify-between items-start z-10 pointer-events-none select-none">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(0,240,255,0.8)]"></div>
            <h1 className="text-2xl font-bold tracking-[0.2em] text-white drop-shadow-md">FLEET REACTOR</h1>
          </div>
          <p className="text-[10px] text-white/40 uppercase font-mono tracking-widest pl-5">Native Spatial Topology • Active Stream</p>
        </div>

        {/* Global Action Controls */}
        <div className="flex items-center gap-4 pointer-events-auto">
           {uiState.selectedNodeId && (
             <div className="flex items-center gap-3 bg-black/40 border border-white/10 backdrop-blur-md px-4 py-2 rounded-lg transition-all shadow-lg">
                <span className="text-[10px] uppercase text-white/50 font-mono">Target Lock</span>
                <span className="text-sm font-mono text-cyan-400 font-bold">{uiState.selectedNodeId}</span>
             </div>
           )}
           <button 
             onClick={toggleBlast}
             disabled={!uiState.selectedNodeId}
             className={`px-6 py-3 rounded-lg border backdrop-blur-md text-xs font-bold uppercase tracking-widest transition-all duration-300 
               ${uiState.blastMode 
                 ? 'bg-red-500/20 border-red-500 text-red-400 shadow-[0_0_20px_rgba(255,0,0,0.4)]' 
                 : (uiState.selectedNodeId ? 'bg-white/5 border-white/20 text-white hover:bg-white/10 hover:border-cyan-500/50 hover:text-cyan-400 hover:shadow-[0_0_15px_rgba(0,240,255,0.2)]' : 'bg-transparent border-white/5 text-white/10 cursor-not-allowed')
               }`}
           >
             {uiState.blastMode ? '[ Cancel Sonar ]' : '[ Blast Radius Sonar ]'}
           </button>
        </div>
      </div>

      {/* Floating Legend */}
      <div className="absolute bottom-8 left-8 flex flex-col gap-3 z-10 pointer-events-none bg-black/40 border border-white/10 p-5 rounded-xl backdrop-blur-md select-none shadow-2xl">
         <div className="text-[10px] uppercase font-mono text-white/50 tracking-widest mb-2 border-b border-white/10 pb-2">Resonance State</div>
         <div className="flex items-center gap-4 text-xs font-mono"><div className="w-2 h-2 rounded-full bg-[#00f0ff] shadow-[0_0_10px_#00f0ff]"></div> Processing</div>
         <div className="flex items-center gap-4 text-xs font-mono"><div className="w-2 h-2 rounded-full bg-[#ffaa00] shadow-[0_0_10px_#ffaa00]"></div> Awaiting I/O</div>
         <div className="flex items-center gap-4 text-xs font-mono"><div className="w-2 h-2 rounded-full bg-[#ff0055] shadow-[0_0_10px_#ff0055]"></div> Blocked</div>
         <div className="flex items-center gap-4 text-xs font-mono"><div className="w-2 h-2 rounded-full bg-[#00ffaa] shadow-[0_0_10px_#00ffaa]"></div> Sequence Complete</div>
      </div>

      {/* Spatial Radial Menu (Projected dynamically from 3D coords) */}
      <div 
        ref={radialMenuRef}
        className="absolute top-0 left-0 w-64 h-64 pointer-events-none opacity-0 transition-opacity duration-300 z-40 select-none flex items-center justify-center"
        style={{ transformOrigin: 'center center' }}
      >
        {/* Pulsing Target Reticle */}
        <div className="absolute w-24 h-24 border border-cyan-500/30 rounded-full animate-[spin_4s_linear_infinite] border-t-cyan-500 shadow-[0_0_15px_rgba(0,240,255,0.2)]"></div>
        <div className="absolute w-32 h-32 border border-white/10 rounded-full animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite]"></div>

        {/* Action Nodes */}
        <button onClick={() => handleAction('stop')} className="absolute -top-6 left-1/2 -translate-x-1/2 w-16 h-16 rounded-full bg-black/80 border border-red-500/50 text-red-400 hover:bg-red-500/20 hover:border-red-500 hover:text-red-300 hover:scale-110 hover:shadow-[0_0_25px_rgba(255,0,85,0.6)] backdrop-blur-xl transition-all duration-300 flex items-center justify-center text-[10px] font-bold uppercase tracking-wider pointer-events-auto cursor-pointer">
          Stop
        </button>
        <button onClick={() => handleAction('steer')} className="absolute top-1/2 -right-6 -translate-y-1/2 w-16 h-16 rounded-full bg-black/80 border border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/20 hover:border-cyan-500 hover:text-cyan-300 hover:scale-110 hover:shadow-[0_0_25px_rgba(0,240,255,0.6)] backdrop-blur-xl transition-all duration-300 flex items-center justify-center text-[10px] font-bold uppercase tracking-wider pointer-events-auto cursor-pointer">
          Steer
        </button>
        <button onClick={() => handleAction('apprv')} className="absolute -bottom-6 left-1/2 -translate-x-1/2 w-16 h-16 rounded-full bg-black/80 border border-green-500/50 text-green-400 hover:bg-green-500/20 hover:border-green-500 hover:text-green-300 hover:scale-110 hover:shadow-[0_0_25px_rgba(0,255,170,0.6)] backdrop-blur-xl transition-all duration-300 flex items-center justify-center text-[10px] font-bold uppercase tracking-wider pointer-events-auto cursor-pointer">
          Apprv
        </button>
        <button onClick={() => handleAction('deny')} className="absolute top-1/2 -left-6 -translate-y-1/2 w-16 h-16 rounded-full bg-black/80 border border-amber-500/50 text-amber-400 hover:bg-amber-500/20 hover:border-amber-500 hover:text-amber-300 hover:scale-110 hover:shadow-[0_0_25px_rgba(255,170,0,0.6)] backdrop-blur-xl transition-all duration-300 flex items-center justify-center text-[10px] font-bold uppercase tracking-wider pointer-events-auto cursor-pointer">
          Deny
        </button>
      </div>

      {/* Multimodal Voice Integration Bar */}
      <div className="absolute bottom-10 left-1/2 -translate-x-1/2 z-40 pointer-events-auto">
        <button 
          className="group flex items-center gap-4 bg-black/60 border border-white/10 hover:border-cyan-500/50 backdrop-blur-md px-6 py-4 rounded-full shadow-2xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(0,240,255,0.15)] cursor-pointer"
          onClick={() => console.log('[VOICE] Multimodal channel opened')}
        >
          <div className="relative flex items-center justify-center">
            <div className="w-3 h-3 rounded-full bg-cyan-400 group-hover:animate-ping absolute opacity-50"></div>
            <div className="w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_10px_#00f0ff] relative"></div>
          </div>
          <span className="text-sm font-mono text-white/50 group-hover:text-cyan-400 transition-colors uppercase tracking-widest">
            [ Ask The Fleet ]
          </span>
          <div className="flex gap-1 items-center h-4 ml-2 opacity-30 group-hover:opacity-100 transition-opacity">
            <div className="w-1 bg-cyan-400 rounded-full h-1 group-hover:animate-[pulse_1s_ease-in-out_infinite]"></div>
            <div className="w-1 bg-cyan-400 rounded-full h-2 group-hover:animate-[pulse_1.2s_ease-in-out_infinite]"></div>
            <div className="w-1 bg-cyan-400 rounded-full h-3 group-hover:animate-[pulse_0.8s_ease-in-out_infinite]"></div>
            <div className="w-1 bg-cyan-400 rounded-full h-1 group-hover:animate-[pulse_1.4s_ease-in-out_infinite]"></div>
          </div>
        </button>
      </div>
      
      {/* 2100 Era Scanline Overlay (pure CSS) */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50 bg-[repeating-linear-gradient(transparent,transparent_2px,#000_2px,#000_4px)]"></div>
    </div>
  );
}
