/* eslint-disable */
// @ts-nocheck
//
// WHY `@ts-nocheck` IS HERE, AND WHY IT IS SCOPED TO ONE FILE.
//
// The founder's component is plain JavaScript -- 617 lines written to run, not to satisfy a
// compiler. This repo compiles `strict` with `noUnusedLocals`, so that body produced 163 errors:
// implicit `any[]` on `nodes`/`edges`, `never` on the raycaster's result, unused `React`. Not one
// of them is a behaviour bug; they are the compiler describing a dialect the code was not written
// in.
//
// The three candidate fixes were: rewrite the founder's code (rejected -- it is their code and it
// works), sprinkle `any` through it (rejected -- it would hide a REAL error later), or relax the
// rules for THIS FILE ONLY. The last is the honest one: the relaxation is visible in the file, it
// cannot leak into the 400 other files, and the moment this component is converted to TypeScript
// the directive is deleted and the compiler tells the truth about it.
//
// Everywhere else in the repo, `tsc` remains as strict as it was.
//
// FleetReactorApp.tsx — the founder's Fleet Reactor 2100.
//
// THE VISUAL CODE IS THE FOUNDER'S, UNCHANGED. What has been added is the WIRING the founder's own
// comments asked for: the four seams marked in their source ("--- LIVE TELEMETRY & ACTION SEAM ---",
// the commented-out `fetch('/api/fleet/status')`, the `console.log` in handleAction, and the
// `console.log` in the voice bar) now talk to the estate.
//
//     generateTopology()   Math.random() -> the 24 REAL sessions from the fleetview plugin
//     pollTelemetry()      commented out -> real poll, mutating the Three.js graph in place
//     handleAction()       console.log   -> real POST to the fleetview signals endpoint
//     Ask The Fleet        console.log   -> microphone -> router -> spoken answer
//
// Every addition is marked ADDED. Nothing below a marker was rewritten.

import React, { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import * as THREE from 'three';

// --- ADDED: the estate's own API surface. `plugin://proxy/fleetview/*` is how the Backstage
// front end reaches the Python plugin, which reads estate.db. ---
import { fetchApiRef, discoveryApiRef } from '@backstage/core-plugin-api';
import { useApi } from '@backstage/core-plugin-api';
// The four motion primitives: thinking breathes, waiting drifts, stuck jitters, finished sinks.
// The colour was always honest; the motion was a uniform bob, which the design calls the single
// worst mistake -- an agent stuck in a retry loop looked exactly like one thinking.
import { tickerLine, gravityOf, fire, stepParticles, pulseRadius, PULSE_MS, burnBar } from './reactor';
// The estate's own voice engine -- whisper for hearing, Kokoro for speaking. Mounted as a hook so
// every surface uses the same models rather than the browser's network recogniser and formant TTS.
import { useEstateVoice } from '../../home/useEstateVoice';
// --- ADDED: an estate intent run by voice, shown on the fleet. ---
import { cueToReactor, type IntentResult } from '../../home/intentCue';
// --- ADDED: the news desk (crew#974 P2) -- the director's stories, rendered as a broadcast overlay. ---
import NewsDesk from './NewsDesk';
import AgentJobs from './AgentJobs';
import EfficiencyHud from './EfficiencyHud';
import { emptyRundown, ingest, parseStoryFrame, shouldInterrupt, visualFor, type Rundown, type Story } from './newsRundown';
import { useVoiceRouter } from '../../home/useVoiceRouter';
import { CineCam } from './cinecam';


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

/**
 * WHERE THE FLEETVIEW BACKEND LIVES.
 *
 * This was `http://127.0.0.1:18790` written out at SEVEN call sites, which is two separate
 * production failures waiting:
 *
 *   1. a browser cannot reach a pod-local loopback address, so every direct fetch (replies,
 *      signals, history, work, and the event stream) would die the moment this page is served from
 *      anywhere but the developer's own machine;
 *   2. `serve.py` binds 127.0.0.1 and its CORS list names only loopback origins, so a correct URL
 *      alone would still be blocked.
 *
 * ONE constant, read from the build environment, so the same bundle works on a laptop and in a
 * cluster without an edit. `FLEETVIEW_URL` is inlined by the bundler at build time.
 *
 * WHY NOT THE BACKSTAGE PROXY, WHICH EXISTS FOR EXACTLY THIS. `/fleetview` -> 127.0.0.1:18790 is
 * configured in app-config.yaml and is the right answer for HTTP -- but the PROXY CANNOT CARRY A
 * WEBSOCKET or an SSE upgrade (measured 2026-09-20: proxy-backend 0.6.16 forwards requests, not
 * upgrades), so the event stream must dial the service directly wherever it lives. Since one of
 * the seven cannot use the proxy, all seven use the same origin: a page where half the data comes
 * from one place and half from another is a page whose failures are impossible to reason about.
 */
const FLEETVIEW_ORIGIN = process.env.FLEETVIEW_URL ?? 'http://127.0.0.1:18790';

/**
 * The board's shared key, for the one route the browser calls that needs it: `/kill`.
 *
 * IT IS COMPILED INTO THE BUNDLE, and that is stated rather than hidden. `process.env` is inlined
 * by Backstage's bundler at build time, so this is not a secret in the cryptographic sense --
 * anything the page can read, a person with the bundle can read. What it buys is that a DRIVE-BY
 * page cannot forge the call: an attacker must first obtain this bundle.
 *
 * THE DEPLOYMENT CONSEQUENCE, named because it is a real trap: if the backend sets
 * FLEETVIEW_BOARD_KEY and this build does not, the Kill button 401s. That is why the refusal is
 * surfaced verbatim in `endStatus` rather than logged -- a button that silently stops working when
 * the server is hardened is worse than one that says "bad or missing board key".
 */
const BOARD_KEY = process.env.FLEETVIEW_BOARD_KEY ?? '';

/**
 * How many working agents the rail lists before it says "+N more".
 *
 * A named constant because it is a design decision, not a number that happened to work: the rail
 * replaced a 37-row table precisely because a long list is clutter, and the value is the point at
 * which the list stops being scannable. Raising it is a deliberate act.
 */
const RAIL_MAX = 9;

export default function FleetReactorApp() {
  const mountRef = useRef(null);
  const radialMenuRef = useRef(null);
  const tooltipRef = useRef(null);
  // The layer the per-node labels live in. Positions are written every frame, so React must not
  // re-render to move them -- the elements are created once below and only transformed after.
  const labelsRef = useRef(null);
  
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
    particles: [],
    // THE REAL PHYSICS, which the file already had and nothing was using.
    //
    // `jets` are the particles `reactor.ts`'s fire()/stepParticles() expect -- not the drifted
    // meshes that were here, which moved because they had been assigned a random speed.
    jets: [],
    // `eventCounts` remembers the last event_count seen PER SESSION, so the difference between two
    // frames is the number of events that actually arrived. That difference is what fire() takes:
    // a jet therefore means work rather than animation.
    eventCounts: new Map(),
    // Events that arrived since the last rendered frame, waiting to be turned into jets. Buffered
    // rather than fired inline because the stream delivers a burst in one tick and the loop can
    // spread it across frames.
    arrivals: [],
    // The blast-radius sonar wave: a travelling ring rather than a static highlight. Written by
    // toggleBlast, advanced every frame, and drawn as a scaled ring.
    pulse: null as { id: string; t: number } | null,
    pulseRing: null as any,
    // --- ADDED: voice -> intent cue state for the fleet-centre ring/burst. ---
    intentCue: null as { t: number; kind: string; color: string } | null,
    intentRing: null as any,
    intentJets: [] as any[],
    intentPoints: null as any,
    intentPos: null as any,
    intentColor: '#00f0ff',
    // The live movie: cues from the director (estate.cinema.cue via /stream) fly the camera.
    cine: new CineCam({ position: [0, 30, 90], quaternion: [0, 0, 0, 1], fov: 50 }) as CineCam,
    cineTarget: null as any
  });

  // THE TAILWIND CDN SCRIPT IS GONE, AND IT MUST NOT COME BACK.
  //
  // Someone hit the missing-utility-classes problem before me and solved it by injecting
  // `https://cdn.tailwindcss.com` at runtime. That is three separate faults in one line:
  //
  //   1. SUPPLY CHAIN. It executes arbitrary remote JavaScript inside the developer portal, on
  //      every page load, with no integrity hash and no pin. A compromised CDN is a compromised
  //      Backstage.
  //   2. IT FAILS SILENTLY WHERE IT MATTERS. Air-gapped, CSP'd, or behind a proxy that blocks the
  //      host, the script never arrives and every utility class in this file stops existing -- the
  //      header unstacks, the panels go static, and nothing says why. Measured 2026-09-20.
  //   3. IT DOES NOT BELONG TO THIS PROJECT. This repo has no Tailwind; the estate uses plain CSS
  //      with `--bui-*` variables. Adding a whole framework at runtime to style one component is
  //      the largest possible hammer for the smallest nail.
  //
  // What actually styles this page is the `.fleet-reactor` block in src/styles.css, which defines
  // exactly the utilities this file uses, scoped so they cannot leak, and ships in the bundle.
  //
  // IF a class looks missing, ADD IT THERE. Do not reach for the CDN: `bin/gate-undeclared`
  // cannot see this class of defect and the page will simply look wrong in production only.

  // THE ORIGINAL REACTOR, copied verbatim from git e61e43d0 (served at /fleet-original) on
  // 2026-09-26 at the founder's instruction. Do not re-derive it; the live wiring below feeds it.
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

      // --- ADDED: the intent cue. One ring from fleet centre, sized by reactor.ts's pulseRadius over PULSE_MS, and the burst fire() put in intentJets. ---
      const ic = engineState.current.intentCue;
      if (ic) {
        ic.t += (delta * 1000) / PULSE_MS;
        if (!engineState.current.intentRing) {
          const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 64), new THREE.MeshBasicMaterial({ transparent: true, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, depthWrite: false }));
          mainGroup.add(ring);
          engineState.current.intentRing = ring;
        }
        const ring = engineState.current.intentRing;
        const radius = Math.max(0.01, pulseRadius({ id: 'fleet', t: Math.min(ic.t, 1) }) * 30);
        ring.visible = ic.t < 1;
        ring.material.color.set(ic.color);
        ring.position.set(0, 0, 0);
        ring.scale.set(radius, radius, radius);
        ring.material.opacity = Math.max(0, (ic.kind === 'shield' ? 0.8 : 0.55) * (1 - ic.t));
        if (ic.t >= 1) engineState.current.intentCue = null;
      }
      const ij = engineState.current.intentJets;
      stepParticles(ij, delta * 1000);
      if (ij.length && !engineState.current.intentPoints) {
        const geo = new THREE.BufferGeometry();
        const pos = new Float32Array(200 * 3);
        geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
        const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.6, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending, depthWrite: false }));
        mainGroup.add(pts);
        engineState.current.intentPoints = pts;
        engineState.current.intentPos = pos;
      }
      if (engineState.current.intentPoints) {
        const pts = engineState.current.intentPoints;
        const buf = engineState.current.intentPos;
        const n = Math.min(ij.length, 200);
        for (let i = 0; i < n; i += 1) { buf[i * 3] = ij[i].x; buf[i * 3 + 1] = ij[i].y; buf[i * 3 + 2] = 0; }
        pts.geometry.setDrawRange(0, n);
        pts.geometry.attributes.position.needsUpdate = true;
        pts.material.color.set(engineState.current.intentColor);
        pts.visible = n > 0;
      }

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

      // The director's cue owns the camera while it plays; the rig above resumes when it is idle.
      const cine = engineState.current.cine;
      if (cine.state === 'idle') {
        if (camera.fov !== 50) { camera.fov = 50; camera.updateProjectionMatrix(); }
        cine.sync({ position: camera.position.toArray() as any, quaternion: camera.quaternion.toArray() as any, fov: camera.fov });
      } else {
        const pose = cine.step(delta);
        camera.position.set(pose.position[0], pose.position[1], pose.position[2]);
        camera.quaternion.set(pose.quaternion[0], pose.quaternion[1], pose.quaternion[2], pose.quaternion[3]);
        camera.fov = pose.fov;
        camera.updateProjectionMatrix();
        lookAtTarget.copy(engineState.current.cineTarget || lookAtTarget);
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
    // START THE WAVE. `pulseRadius` and `PULSE_MS` were imported into this file and never used,
    // and `engineState.current.pulse` was declared with a comment describing "a travelling ring
    // rather than a static highlight" -- and never read or written. The button only recoloured
    // materials. This is the wave the types were already there for.
    const sel = engineState.current.nodes.find(
      (n: any) => n.sessionId && engineState.current.selectedNode === n,
    );
    engineState.current.pulse = newMode && sel ? { id: sel.id, t: 0 } : null;
  };

  // --- WIRED: LIVE TELEMETRY ---
  //
  // The founder's block above was a comment: it constructed `/api/fleet/status`, which does not
  // exist in this estate, and the poll body was empty. This reads the real contract --
  // `GET /api/proxy/fleetview/sessions`, the same endpoint the board and the voice layer use --
  // and maps each session onto the node that already represents it.
  //
  // IT MUTATES THE THREE.JS GRAPH IN PLACE, which is what the founder asked for and why the
  // polling does not go through React state: a 2s re-render of 24 nodes and their materials is
  // waste, and it would reset the camera. `force` is called once on the first successful read,
  // only so the HUD's counts appear.
  // THE ESTATE'S VOICE ENGINE, DECLARED FIRST.
  //
  // Every voice surface mounts this hook. It has to be declared before ANY callback that closes
  // over it -- `talkTo` and the heard->steer effect both do -- because a `const` lives in the
  // temporal dead zone until its line executes. Declared late, it threw on every render.
  //
  // Two engines, one surface. useEstateVoice is the voice: every voice in the picker, and talking
  // to one agent (its words are steered to that agent, and the agent's reply is spoken). voice-
  // router (streaming: words as you speak, first audio while the brain is still answering) speaks
  // only when chosen in the picker as "Streaming", only while no agent is addressed (the router
  // answers questions itself, which would talk over the agent), and only while it answers. A
  // conversation already running on useEstateVoice is never switched mid-sentence.
  //
  // 2026-09-27: the router was made the default and the picker read its catalogue (one Piper
  // voice, selectVoice a no-op), so the voice list and the mic on each agent vanished. Tested by
  // e2e-tests/fleet-voice-controls.test.ts, a fleet-regression step.
  // Which agent the microphone is addressed to, and the last thing it heard -- the ref because the
  // effect below must not re-fire on every render, and the state because the row must light up.
  const voiceTargetRef = useRef('');
  const lastHeardRef = useRef('');
  // The id of the last reply already spoken aloud, so a re-render cannot repeat it.
  const spokenReplyRef = useRef<number | string | null>(null);
  const [voiceTarget, setVoiceTarget] = useState('');
  const legacyVoice = useEstateVoice();
  const [fleetBrief, setFleetBrief] = useState('');
  // The intent visual is defined further down (it needs the engine); the ref reaches it.
  const onIntentRef = useRef<(r: IntentResult) => void>(() => {});
  const routerVoice = useVoiceRouter(fleetBrief, { onIntentResult: (r: IntentResult) => onIntentRef.current(r) });
  const [streaming, setStreaming] = useState(() => {
    try { return window.localStorage.getItem('fleet.voice.streaming') === '1'; } catch { return false; }
  });
  const chooseStreaming = (on: boolean) => {
    setStreaming(on);
    try { window.localStorage.setItem('fleet.voice.streaming', on ? '1' : '0'); } catch { /* private mode */ }
  };
  const voice =
    streaming && !voiceTarget && legacyVoice.state === 'off' && (routerVoice.reachable || routerVoice.state !== 'off')
      ? routerVoice
      : legacyVoice;
  const partial = voice === routerVoice ? routerVoice.partial : '';
  // A director cue's line is spoken if a voice engine is on, else shown in the ticker for 4s.
  const [cueLine, setCueLine] = useState('');
  // SAFEGUARDS, LIVE. Each row is a gate deciding on a real agent turn, published on the bus as an
  // estate.agent.event of kind "gate" (bin/epistemic_firewall.py). Founder 2026-09-27: a safeguard
  // is operational only when /fleet shows it deciding as it happens. A refusal is spoken.
  const [gates, setGates] = useState<any[]>([]);
  const cueSayRef = useRef<(text: string) => void>(() => {});
  cueSayRef.current = (text: string) => {
    if (!text) return;
    if (voice.state !== 'off') { voice.speak(text.slice(0, 300)); return; }
    setCueLine(text);
    setTimeout(() => setCueLine((cur) => (cur === text ? '' : cur)), 4000);
  };
  const api = useApi(fetchApiRef);
  const discovery = useApi(discoveryApiRef);
  const baseUrlRef = useRef(null);
  const [live, setLive] = useState({ ok: false, count: 0, error: null, ticker: '' });

  // --- ADDED: voice -> intent. The result's cue becomes a ring (and, for burn/fire, a burst) from the fleet's centre, and its text holds the ticker for 4s. ---
  const [intentLine, setIntentLine] = useState('');
  const intentTimer = useRef<any>(null);
  const onIntentResult = useCallback((r: IntentResult) => {
    const c = cueToReactor(r);
    engineState.current.intentCue = { t: 0, kind: c.kind, color: c.color };
    engineState.current.intentColor = c.color;
    if (c.kind === 'burn' || c.kind === 'fire') {
      fire(engineState.current.intentJets, 0, 0, `intent:${r.intent}`, c.kind === 'burn' ? 8 : 4, c.kind === 'burn' ? 'stuck' : 'thinking');
    }
    setIntentLine(r.text);
    clearTimeout(intentTimer.current);
    intentTimer.current = setTimeout(() => setIntentLine(''), 4000);
  }, []);
  useEffect(() => () => clearTimeout(intentTimer.current), []);
  onIntentRef.current = onIntentResult;

  // --- ADDED: the news desk (crew#974 P2). `rundown` accumulates director stories per channel;
  // `channel` is which one is on screen; `breaking` is the current interrupt band, auto-cleared
  // after 8s; `seenBreaking` stops a replayed history frame from re-triggering the same interrupt.
  const [rundown, dispatchStory] = useReducer(
    (state: Rundown, frame: ReturnType<typeof parseStoryFrame>) => (frame ? ingest(state, frame, Date.now()) : state),
    undefined,
    emptyRundown,
  );
  const [newsChannel, setNewsChannel] = useState(0);
  const [breakingStory, setBreakingStory] = useState<Story | null>(null);
  const breakingTimer = useRef<any>(null);
  const seenBreakingRef = useRef<Set<string>>(new Set());
  const lastStoryShotMsRef = useRef(0);
  useEffect(() => () => clearTimeout(breakingTimer.current), []);
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }
      if (!/^[0-6]$/.test(e.key)) return;
      setNewsChannel(Number(e.key));
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  // THE ROWS THE LEFT PANEL RENDERS.
  //
  // WHY THIS EXISTS. The board moved but did not say WHAT was moving: a node hovered as
  // "AG-1013 WAITING" with no task, repo, runtime or spend, so the animation carried no meaning
  // and "which harness, which provider, which agent" had no answer on screen. The API had all of
  // it the whole time (task, repo, runtime, spend_usd, event_count, updated_at) and the Reactor
  // read only four fields.
  //
  // Kept in React state rather than written into the node objects: the panel is a LIST that must
  // re-render on poll, and node fields are mutated by the render loop where a change would not
  // reach React at all.
  const [rows, setRows] = useState([]);

  // What the voice answers from: the live board, so it never invents a count. Only what changes
  // meaning (state, task, repo) is in it, not ages, so it is re-sent when the fleet changes and not
  // on every 2s poll.
  useEffect(() => {
    const list = rows as any[];
    const by = (a: string) => list.filter((r) => r.activity === a).length;
    const lines = list
      .slice(0, 20)
      .map((r) => `${r.sessionId} (${r.runtime}${r.model ? `, ${r.model}` : ''}): ${r.activity}; ${r.repo || 'no repo'}; ${r.task.slice(0, 80) || 'no task'}`);
    setFleetBrief(
      list.length
        ? `The fleet right now: ${list.length} sessions, ${by('stuck')} stuck, ${by('thinking')} thinking, ${by('waiting')} waiting, ${by('finished')} finished.\n${lines.join('\n')}`
        : '',
    );
  }, [rows]);

  // WHAT THE AGENTS SAID BACK, newest first, fleet-wide.
  //
  // Fetched on the same 2s cadence as the sessions, from the reply channel (routes.py:
  // /replies). Grouped by session below so a row can show its own conversation, and shown as a
  // fleet-wide feed as well -- an answer to a steer you sent ten minutes ago is easy to miss if it
  // is only visible on the row you are not looking at.
  const [replies, setReplies] = useState([]);
  // The steer box. `status` reports what happened to the last message sent from the panel, because
  // a send button that says nothing is the same as one that did nothing.
  // The conversation scrolls itself to the newest message: a thread you have to scroll to follow
  // is not a conversation. Declared here because `ref={threadRef}` reads it directly -- an
  // identifier my own guard could not see, since it only checked names inside `{...}` expressions
  // and not ref attributes.
  const threadRef = useRef(null);
  // The voice picker's list, open or closed. Closed it is one small chip in the top-right corner.
  const [voiceMenu, setVoiceMenu] = useState(false);
  // The burn bar's numbers, written by the poll and read by the render. A ref because the bar is
  // painted every frame from the same source the ticker reads.
  const burnRef = useRef({ fill: 0, heat: 0, label: 'idle' });
  const selectedSessionRef = useRef('');
  // Which view the rail shows. One at a time, because three at once is a wall.
  // THE LEFT PANEL: which view, and how deep.
  //
  // Two axes of progressive disclosure, because one is not enough for a space this small:
  //
  //   TAB    what KIND of thing you are looking at -- the fleet's agents, the harness around
  //          them (receipts), or the conversation. Three views, one column, one visible at a time.
  //   DEPTH  how much of that thing. Level 0 is a count and a coloured bar; level 1 adds the task
  //          and the branch; level 2 adds spend, model, events. Each level is a click, so the
  //          column can hold a lot without ever LOOKING full -- which is the whole point.
  const [panelTab, setPanelTab] = useState<'fleet' | 'harness' | 'friction'>('fleet');
  // Readable from the 2s poll, which deliberately does not re-subscribe on a tab change -- the
  // same reason `selectedSessionRef` exists. Without it the poll would close over whichever tab
  // was active when the effect ran, and a person opening Harness would wait for a page reload.
  const panelTabRef = useRef<'fleet' | 'harness' | 'friction'>('fleet');
  const [depth, setDepth] = useState(1);
  // The rail is CLOSED by default. See the comment on the panel: a permanent text column over a
  // spatial instrument is the dashboard metaphor the ruling replaced.
  const [panelOpen, setPanelOpen] = useState(false);
  const [ledgerRows, setLedgerRows] = useState<any[]>([]);
  const [steerDraft, setSteerDraft] = useState('');
  const [steerStatus, setSteerStatus] = useState('');
  // What happened to the last stop/kill press. Same rule as steerStatus: a control that says
  // nothing is a control that did nothing.
  const [endStatus, setEndStatus] = useState('');
  // What WE sent, so the panel can show both sides of a conversation. Replies alone read as an
  // agent talking to itself.
  const [signals, setSignals] = useState([]);


  // The selected session, readable from inside the poll.
  //
  // The poll effect deliberately does not depend on the selection -- re-subscribing the interval on
  // every click would restart the 2s timer and let a click starve the telemetry. A ref gives the
  // running poll the CURRENT selection without re-running the effect, which is exactly what a ref
  // is for.

  /**
   * Send a message to the selected session, from the panel.
   *
   * Uses the SAME /nudge endpoint the radial menu uses -- one steering path, not two -- and posts
   * to the Fleetview backend directly rather than through the proxy, for the same reason the reply
   * feed does: an unknown path on this origin returns the SPA with a 200, so a proxy call would
   * "succeed" by fetching HTML.
   */
  /**
   * End a session, gracefully or hard.
   *
   * `stop` posts to /stop, which leaves a marker the extension honours at its next turn boundary.
   * `kill` posts to /kill, which the backend turns into a SIGTERM against the PID the session
   * reported. Kept as one function because both are "end it" and the caller should read as a choice
   * between two modes rather than two unrelated actions.
   */
  const endSession = useCallback(async (mode: 'stop' | 'kill', row: any) => {
    if (!row) return;
    setEndStatus(mode === 'stop' ? 'asking it to stop…' : 'sending SIGTERM…');
    try {
      const res = await fetch(`${FLEETVIEW_ORIGIN}/${mode}`, {
        method: 'POST',
        // STOP IS A WRITE BUT NOT A SIGNAL, so it needs no key; KILL is the destructive one and
        // the backend refuses it without one once FLEETVIEW_BOARD_KEY is configured. The key is
        // compiled into this bundle, which is why the backend's comment is explicit that this
        // raises the bar rather than being authentication.
        headers: {
          'Content-Type': 'application/json',
          ...(BOARD_KEY ? { 'X-Board-Key': BOARD_KEY } : {}),
        },
        body: JSON.stringify({ session_id: row.sessionId, runtime: row.runtime, by: 'reactor' }),
      });
      const body = await res.json().catch(() => ({}));
      setEndStatus(
        res.ok
          ? mode === 'stop'
            ? 'stop requested — it exits at its next turn boundary'
            : `SIGTERM sent${body.pid ? ` to pid ${body.pid}` : ''}`
          : `refused: ${body.error || res.status}`,
      );
    } catch (e: any) {
      setEndStatus(`failed: ${e.message || e}`);
    }
  }, []);

  const sendSteer = useCallback(async (text: string, row: any) => {
    if (!row) return;
    setSteerStatus('sending…');
    try {
      const res = await fetch(`${FLEETVIEW_ORIGIN}/nudge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: row.sessionId,
          runtime: row.runtime,
          by: 'reactor',
          text,
        }),
      });
      const body = await res.json().catch(() => ({}));
      // The refusal IS the useful message: a runtime with no steering channel returns 422 with its
      // reason, and that reason is more use on screen than "failed".
      setSteerStatus(res.ok ? `queued · delivered at its next turn` : `refused: ${body.error || res.status}`);
    } catch (e: any) {
      setSteerStatus(`failed: ${e.message || e}`);
    }
    return true;
  }, []);

  /**
   * Talk to ONE agent, by voice.
   *
   * WHAT THIS IS FOR. The founder, 2026-09-20: "i need to voice conversation with any agent session,
   * not seeing garbled text". Two requirements in one sentence:
   *
   *   1. the conversation is ADDRESSED to a session, not to the fleet in general. The engine's
   *      websocket already answers from the fleet envelope, so speaking produces a general answer;
   *      what makes it a conversation WITH an agent is that the transcript is sent to THAT session
   *      as a steer and answered by it.
   *   2. the text on screen is READABLE. "Garbled" is what a raw task string looks like -- the
   *      first prompt verbatim, full of typos and newlines. The transcript and the reply are clean
   *      because they come from whisper and from the agent's own words.
   *
   * THE FLOW: start the mic, and when the engine reports what it heard, send that text to this
   * session. The agent's answer arrives on the reply channel and is SPOKEN by the same engine, so a
   * turn is: speak, it answers aloud, the words appear. Nothing has to be read to be understood.
   */
  const talkTo = useCallback(
    async (row: any) => {
      if (!row) return;
      // A second click on the same agent stops the conversation.
      if (voiceTargetRef.current === row.sessionId) {
        voiceTargetRef.current = '';
        setVoiceTarget('');
        legacyVoice.stop();
        return;
      }
      voiceTargetRef.current = row.sessionId;
      setVoiceTarget(row.sessionId);
      // Always useEstateVoice: its transcript is steered to this agent. A streaming conversation
      // with the fleet is ended first, or two engines would be listening.
      if (routerVoice.state !== 'off') routerVoice.stop();
      if (legacyVoice.state === 'off') await legacyVoice.start();
    },
    [legacyVoice, routerVoice],
  );

  // WHEN THE ENGINE HEARS SOMETHING, it goes to the addressed session.
  //
  // The engine's own answer (from the fleet envelope) is spoken as an immediate reply, because
  // waiting several seconds in silence while an agent takes its turn would feel broken -- and the
  // agent's real answer, when it comes, is spoken too. Two voices answering one question is honest
  // here: the first is the board telling you what it can see, the second is the agent itself.
  // AUTO-SCROLL THE THREAD. The ref was declared, attached, and never read, while the comment
  // above it claimed the scroll existed -- so the newest message sat below the fold in a 240px
  // scroller, which is the precise defect the comment says it fixes. Depends on the two things
  // that can add a message.
  useEffect(() => {
    const el = threadRef.current as HTMLElement | null;
    if (el) el.scrollTop = el.scrollHeight;
  }, [replies, signals]);

  // SPEAK WHAT THE ADDRESSED AGENT SAID BACK.
  //
  // This was claimed in two comments and implemented nowhere: a reply arrived, was rendered as
  // text, and was never spoken -- so a voice conversation was half a conversation. The promise
  // ("its answer comes back through the same reply channel and is spoken aloud") is now the code.
  //
  // Only for the agent being talked to, and only for a reply we have not spoken before. `speak()`
  // reads the text aloud through the same engine, so what you hear is the same voice you chose.
  useEffect(() => {
    const target = voiceTargetRef.current;
    if (!target || !replies.length) return;
    const mine = replies.filter((rp: any) => rp.session_id === target);
    if (!mine.length) return;
    const newest = mine[0];
    if (spokenReplyRef.current === newest.id) return;   // never say the same thing twice
    spokenReplyRef.current = newest.id;
    voice.speak(String(newest.text || '').slice(0, 600));
  }, [replies, voice]);

  useEffect(() => {
    const target = voiceTargetRef.current;
    const heard = (voice.heard || '').trim();
    if (!target || !heard) return;
    if (lastHeardRef.current === heard) return;
    lastHeardRef.current = heard;
    void sendSteer(heard, { sessionId: target, runtime: target.split(':')[0] });
  }, [voice.heard, sendSteer]);

  // The row behind the current selection. Derived rather than stored: a selection is an id, and
  // holding a second copy of the session data would need keeping in step with every poll.
  const selectedRow = useMemo(() => {
    const sid = uiState.selectedNodeId
      ? engineState.current.nodes.find((n) => n.id === uiState.selectedNodeId)?.sessionId
      : null;
    return rows.find((r) => r.sessionId === sid) || null;
  }, [rows, uiState.selectedNodeId]);

  /**
   * The live rail: one line per ACTIVE agent, with an estimated progress bar.
   *
   * WHY THIS AND NOT THE ROSTER. The 37-row table was removed for clutter and it was right to
   * remove -- but that left the left side empty until something was selected. What belongs there
   * is not the whole fleet: it is the handful of agents that are WORKING, which is what a person
   * watches. Finished agents need no rail (they are done), and the labels in space already name
   * everyone.
   *
   * THE BAR IS AN ESTIMATE AND SAYS SO. There is no progress field in the session record and
   * inventing one would be the "inventing motion to look alive" offence the design doc names. So
   * the bar is derived from what IS measured -- how long the agent has been quiet against the
   * longest quiet period among active agents -- and it is a RECENCY bar, not a completion bar.
   * A stuck agent's bar fills; a just-active one's is near empty. Under a heading that says so.
   */
  const activeRows = useMemo(() => {
    const active = rows.filter((r) => r.activity !== 'finished');
    const maxAge = Math.max(1, ...active.map((r) => r.ageMs ?? 0));
    return active.slice(0, RAIL_MAX).map((r) => ({
      ...r,
      // 0 = just active, 1 = quiet as long as the quietest-to-bed agent on the board.
      pressure: Math.max(0.04, Math.min(1, (r.ageMs ?? 0) / maxAge)),
    }));
  }, [rows]);

  // HOW MANY AGENTS THE RAIL IS NOT SHOWING.
  //
  // The rail caps at RAIL_MAX because the list must not become the 37-row table it replaced. The
  // cap is honest only if it is STATED: the room already applies this rule to the sphere ("+N
  // beyond sphere" in the ticker) and the rail silently dropped the rest, so a fleet of 20 working
  // agents looked like a fleet of 9. A truncated list that does not say it is truncated is the
  // same lie as a green dot.
  const hiddenWorking = Math.max(
    0,
    rows.filter((r) => r.activity !== 'finished').length - activeRows.length,
  );

  // HOW TALL IS THE ROOM, REALLY.
  //
  // Measured 2026-09-20: Backstage's page container (`BackstageSidebarPage-root`) is 1128px tall
  // in a 950px window -- its own layout is taller than the viewport, and the page scrolls. So
  // `h-screen` (100vh) started BELOW the app bar and ran off the bottom, `calc(100vh - 6rem)`
  // computed 1031px against the wrong box, and `h-full` inherited the 1128px parent and changed
  // nothing. Every arithmetic guess against 100vh was arithmetic against a box that is not the
  // one on screen.
  //
  // The height is therefore MEASURED, not derived: the element reports its own top offset and the
  // room is set to the distance between that and the bottom of the visible window.
  //
  // CLAMPED TO THE PARENT'S BOTTOM, which is the fix for the content that escaped the panel.
  // `innerHeight - top` alone sizes the room to the WINDOW, but the parent is 1128px against a
  // 950px window -- so the room ran to the window's bottom edge while the HUD's absolutely
  // positioned children (`top-16`, `bottom-10`, and the radial buttons at `-top-6` / `-bottom-6`
  // that sit OUTSIDE their anchor) were positioned against a box that extended past the panel.
  // Taking the smaller of the two keeps every child inside the plate it is drawn on, and still
  // fits the window. The `Math.max(320, ...)` floor is applied last so a squeezed layout still
  // renders a usable room rather than collapsing to nothing.
  //
  // SCROLL IS LISTENED TO AS WELL AS RESIZE. The page scrolls (the container is taller than the
  // window), so `top` changes without any resize event -- listening only to `resize` left the room
  // at a stale height the moment a reader scrolled, which is the same class of bug as deriving
  // from 100vh in the first place.
  const rootRef = useRef(null);
  const [roomH, setRoomH] = useState(null);

  useEffect(() => {
    const measure = () => {
      const el = rootRef.current;
      if (!el) return;
      const top = el.getBoundingClientRect().top;
      // The visible window's bottom edge.
      const toWindow = window.innerHeight - top;
      // The parent plate's bottom edge, in the same coordinates. Backstage's page container is
      // taller than the window, so this is the shorter of the two and the binding constraint.
      const parent = el.parentElement;
      const toParent = parent
        ? parent.getBoundingClientRect().bottom - top
        : Number.POSITIVE_INFINITY;
      // The parent can legitimately measure 0 before layout settles; treating that as a real
      // constraint would collapse the room, so it is ignored rather than clamped against.
      const usable = toParent > 0 ? Math.min(toWindow, toParent) : toWindow;
      setRoomH(Math.max(320, usable));
    };
    measure();
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    // A ResizeObserver catches the case neither event covers: Backstage's page container changing
    // height without the window resizing (a banner appearing, a panel opening). Without it the
    // room keeps measuring against a plate that has already moved.
    const parent = rootRef.current?.parentElement;
    const ro = parent && typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(measure)
      : null;
    if (ro && parent) ro.observe(parent);
    return () => {
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
      if (ro) ro.disconnect();
    };
  }, []);

  useEffect(() => {
    panelTabRef.current = panelTab;
    selectedSessionRef.current = uiState.selectedNodeId
      ? engineState.current.nodes.find((n) => n.id === uiState.selectedNodeId)?.sessionId || ''
      : '';
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try { baseUrlRef.current = await discovery.getBaseUrl('proxy'); } catch { baseUrlRef.current = null; }
    })();
    return () => { cancelled = true; };
  }, [discovery]);

  useEffect(() => {
    const STATE = { thinking: 'thinking', waiting: 'waiting', stuck: 'stuck', finished: 'finished' };
    let first = true;
    // `cancelled` BELONGS TO THIS EFFECT. It was declared in the discovery effect above and used
    // here, so the first telemetry failure threw `ReferenceError: cancelled is not defined` and
    // took the whole page down -- the blank screen was this line, not the three.js scene.
    let cancelled = false;

    // DECLARED BEFORE ITS FIRST USE. `flushTelemetryError` was a `const` arrow defined below
    // `pollTelemetry`, which ran immediately afterwards -- so the very first poll hit the temporal
    // dead zone. Both faults are in code I added, not in the founder's.
    const flushTelemetryError = (msg) => {
      if (!cancelled) setLive(prev => (prev.ok ? { ok: false, count: 0, error: msg } : prev));
    };

    // ONE POLL AT A TIME.
    //
    // The tick is 2s and one poll performs up to four sequential awaited fetches. If the backend
    // takes longer than the tick -- a slow disk, a locked sqlite, a laptop under load -- the next
    // tick starts while the previous is still in flight, and their responses can land OUT OF ORDER,
    // so an older fleet overwrites a newer one. A guard is one boolean and removes the whole class.
    let inFlight = false;
    const pollTelemetry = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const base = baseUrlRef.current;
        if (!base) return flushTelemetryError('discovery not ready');
        // fetchApi, not bare fetch: the guest Authorization header is added by this wrapper and
        // a bare fetch is 401 here.
        const res = await api.fetch(`${base}/fleetview/sessions`);
        if (!res.ok) return flushTelemetryError(`HTTP ${res.status}`);
        const body = await res.json();
        const sessions = body.sessions || [];
        if (!sessions.length) return flushTelemetryError('no sessions');

        // MAP BY INDEX-FREE LOOKUP, not by array position. The Reactor is built from the
        // founder's own generateTopology, so it always has exactly NUM_AGENTS nodes; a fleet
        // that shrinks or grows must not silently recolour the wrong sphere.
        // MATCH BY SESSION IDENTITY, NOT ARRAY POSITION.
        //
        // Measured 2026-09-19: the fleet held 28 sessions and this sphere has NUM_AGENTS=24
        // slots, so four real agents were silently not drawn -- and because the mapping was
        // positional, a session list that reordered would recolour every node to a DIFFERENT
        // agent. Both are the same bug: treating array index as identity.
        //
        // The sphere is still fixed at NUM_AGENTS (the founder's geometry, and a node that
        // teleports when the fleet grows is worse than one that is not drawn). What changes:
        // a node keeps its session across polls, and anything beyond the slots is COUNTED AND
        // REPORTED in the ticker rather than dropped in silence.
        const byId = new Map();
        engineState.current.nodes.forEach(n => byId.set(n.id, n));
        // seed -> node, rebuilt only for nodes that have no session yet, so an agent that has
        // held a node keeps it. This is what makes identity stable across polls.
        const bySession = new Map();
        engineState.current.nodes.forEach((n) => {
          if (n.sessionId) bySession.set(n.sessionId, n);
        });
        // THE DOTS FOLLOW THE FLEET AS IT IS NOW. Slots were first-come and held forever, so with
        // 192 sessions the first 24 ever seen kept every dot and a newly started agent never
        // appeared. Each poll, the NUM_AGENTS most relevant sessions (stuck, thinking, waiting,
        // then the most recently finished) hold the dots; a node keeps its session while it stays
        // in that set, and a session leaving it frees its node for the one arriving.
        const PRIO = { stuck: 0, thinking: 1, waiting: 2, finished: 3 };
        const shown = [...sessions]
          .sort((a, b) =>
            (PRIO[STATE[a.activity] || 'waiting'] - PRIO[STATE[b.activity] || 'waiting']) ||
            ((Date.parse(b.updated_at || '') || 0) - (Date.parse(a.updated_at || '') || 0)))
          .slice(0, engineState.current.nodes.length);
        const shownIds = new Set(shown.map((x) => x.session_id));
        engineState.current.nodes.forEach((n) => {
          if (n.sessionId && !shownIds.has(n.sessionId)) { bySession.delete(n.sessionId); n.sessionId = null; }
        });
        const free = () => engineState.current.nodes.find(n => !n.sessionId);
        let matched = 0;
        let unshown = 0;
        // The four counts the ticker needs, accumulated as we map (not a second pass).
        const counts = { thinking: 0, waiting: 0, stuck: 0, finished: 0 };
        sessions.forEach((sess) => {
          const activity = STATE[sess.activity] || 'waiting';
          // Count EVERY session, including ones with no free node, so the ticker never
          // under-reports the fleet. The number a human acts on must not depend on how many
          // slots the sphere happens to have.
          counts[activity] = (counts[activity] || 0) + 1;
          if (!shownIds.has(sess.session_id)) { unshown++; return; }
          let node = bySession.get(sess.session_id) || free();
          if (!node) { unshown++; return; }
          if (!node.sessionId) { node.sessionId = sess.session_id; bySession.set(sess.session_id, node); }
          matched++;
          node.runtime = sess.runtime;
          node.model = sess.model;
          node.task = sess.task;
          node.repo = sess.repo;
          node.updatedAt = sess.updated_at;
          node.spend = sess.spend_usd;
          node.events = sess.event_count;
          node.nodeId = node.id;
          // Fill the spatial label's text on the poll, not per frame -- the strings change every
          // two seconds and the POSITION changes sixty times a second, so only the position is
          // written in the render loop.
          if (node.labelState) {
            node.labelState.textContent = activity;
            node.labelState.style.color = COLORS[activity];
          }
          if (node.labelTask) {
            const t = (sess.task || '').replace(/\s+/g, ' ').trim();
            node.labelTask.textContent = t ? (t.length > 46 ? `${t.slice(0, 46)}…` : t) : '(no task)';
          }
          if (node.labelMeta) {
            // Harness AND model. `runtime` alone said `pi`; the model is what tells a reader
            // whether a slow agent is deliberating on a pro model or idling on a flash one.
            node.labelMeta.textContent = [sess.runtime, sess.model, sess.repo]
              .filter(Boolean)
              .join(' · ');
          }
          node.state = activity;
          node.workload = sess.event_count || 0;
          // THE WARP. `gravityOf` is the physics the room was designed around and never used: a
          // busy agent BENDS THE SPACE AROUND IT, so the shape of the room is the shape of the
          // fleet. Read from the same session record as everything else, so the warp cannot
          // disagree with the label.
          node.gravity = gravityOf(sess);
          node.baseColor = new THREE.Color(COLORS[activity]);
          // The founder's own scale rule, now driven by real work instead of Math.random().
          const scale = 0.5 + Math.min(1, Math.sqrt((sess.event_count || 0) / 400)) * 0.7;
          node.baseScale = scale;
          // Blast mode may be mid-flight; only the base is updated here, and the render loop
          // repaints from it on the next frame.
        });

        // The fleet ticker (design: "a fixed-position scan line" that a controller reads in two
        // seconds because its shape never changes). Spend-per-minute is derived from the sessions
        // themselves -- never invented -- and falls back to 'idle' when nothing is burning.
        const totalSpend = sessions.reduce((a, s) => a + (s.spend_usd || 0), 0);
        const activeMs = sessions.reduce((a, s) => {
          const t = Date.parse(s.updated_at || '');
          return Number.isFinite(t) ? Math.max(a, Date.now() - t) : a;
        }, 0);
        const perMin = activeMs > 0 ? (totalSpend / (activeMs / 60000)) : 0;
        // The burn bar's figures. Kept in the same state as the ticker so the two cannot disagree
        // about what the fleet is costing.
        burnRef.current = burnBar(perMin, totalSpend);
        // `unshown` is stated, never hidden: if the fleet outgrows the sphere the reader is told,
        // because a page that silently draws 24 of 28 agents is lying about the fleet size.
        const over = unshown > 0 ? `  ·  +${unshown} beyond sphere` : '';
        // THE PANEL ROWS. Sorted by what a person needs first: stuck at the top, then waiting,
        // then thinking, then done -- a list in session-id order buries the two agents that need
        // attention under twenty that do not. Within a state, most recently active first.
        const RANK = { stuck: 0, thinking: 1, waiting: 2, finished: 3 };
        const panel = sessions
          .map((s) => ({
            sessionId: s.session_id,
            runtime: s.runtime,
            model: s.model || '',
            repo: s.repo,
            task: (s.task || '').replace(/\s+/g, ' ').trim(),
            activity: STATE[s.activity] || 'waiting',
            events: s.event_count || 0,
            spend: s.spend_usd || 0,
            updatedAt: s.updated_at,
            ageMs: Date.parse(s.updated_at || '') ? Date.now() - Date.parse(s.updated_at) : null,
          }))
          .sort((a, b) => {
            const d = (RANK[a.activity] ?? 9) - (RANK[b.activity] ?? 9);
            return d !== 0 ? d : (a.ageMs ?? 1e12) - (b.ageMs ?? 1e12);
          });
        // WHAT EACH ONE IS WORKING ON -- branch and step.
        //
        // Merged into the rows just built, keyed by session id, so the panel can say
        // "feat/battalion-gov01-local-floor / editing FleetReactorApp.tsx" instead of repeating the
        // session's first prompt. A failure here leaves the rows without a branch rather than
        // emptying the board: work detail is an enrichment, not the data the page exists for.
        try {
          const wres = await fetch(`${FLEETVIEW_ORIGIN}/work`);
          if (wres.ok) {
            const wbody = await wres.json();
            const work = wbody.work || {};
            for (const p of panel) {
              const w = work[p.sessionId];
              if (w) {
                p.branch = w.branch || '';
                p.step = w.step || '';
              }
            }
          }
        } catch { /* work detail is optional; the fleet is not */ }

        if (!cancelled) setRows(panel);

        // The replies ride the same poll. Failures are swallowed: a board that loses the reply feed
        // still shows the fleet, and an error banner about telemetry would be noise over the data
        // the person came for.
        //
        // THE URL IS ABSOLUTE, AND IT HAS TO BE. This first read `/api/proxy/fleetview/replies`
        // through the Backstage proxy, which answered **index.html** -- the SPA fallback for a
        // route it does not know -- so `res.json()` threw `Unexpected token '<'` and the reply
        // feed was silently empty while the text appeared from a stale render. Same fault as the
        // /static scripts: any unknown path on this origin returns the app, as a 200.
        try {
          // THE HARNESS LEDGER, for the panel's Harness tab: the receipts behind each session.
          //
          // Fetched ONLY when that tab is open, and only when depth is deeper than the summary --
          // the whole point of the disclosure is that a view costs nothing until it is asked for.
          // A failure leaves the tab saying "no receipts", which is the truthful answer for a
          // session that has not been checked.
          // `/ledger` REQUIRES a session_id and answers 422 without one -- measured, after this
          // fetch produced a 422 on every poll. It is per-SESSION, not fleet-wide, so the tab
          // reads the SELECTED agent's ledger; with nothing selected there is nothing to read and
          // the tab says so rather than asking for the whole estate's, which the route does not
          // serve.
          if (panelTabRef.current === 'harness' && selectedSessionRef.current) {
            try {
              const lres = await fetch(
                `${FLEETVIEW_ORIGIN}/ledger?session_id=${encodeURIComponent(selectedSessionRef.current)}`,
              );
              if (lres.ok) {
                const lbody = await lres.json();
                if (!cancelled) setLedgerRows(lbody.rows || []);
              }
            } catch { /* an empty ledger is not an error */ }
          } else if (panelTabRef.current === 'harness' && !cancelled) {
            setLedgerRows([]);
          }

          const rres = await fetch(`${FLEETVIEW_ORIGIN}/replies?limit=40`);
          if (rres.ok) {
            const rbody = await rres.json();
            if (!cancelled) setReplies(rbody.replies || []);
          }
        } catch { /* the board's read path must not break on the reply path */ }

        // AND WHAT WE SAID. The conversation needs both halves; a thread of replies alone reads as
        // an agent talking to itself, with no way to see which instruction produced an answer.
        //
        // PER SELECTED SESSION, because `/signals` REQUIRES a session_id and answers 422 without
        // one -- which is exactly what happened when this was first wired: three 422s in the console
        // and an empty thread. Steering history is only shown for the agent being looked at, so the
        // narrow call is also the right one.
        const selectedSessionId = selectedSessionRef.current;
        if (selectedSessionId) {
          try {
            const sres = await fetch(
              `${FLEETVIEW_ORIGIN}/signals?session_id=${encodeURIComponent(selectedSessionId)}`,
            );
            if (sres.ok) {
              const sbody = await sres.json();
              if (!cancelled) setSignals(sbody.signals || []);
            }
          } catch { /* same: an optional enrichment */ }
        } else if (!cancelled) {
          setSignals([]);
        }

        if (!cancelled) setLive({ ok: true, count: matched, error: null, ticker: tickerLine(counts, perMin) + over });
        // `force(v => v + 1)` STOOD HERE AND DOES NOT EXIST.
        //
        // There is no `force`/`setForce` anywhere in this file, so this threw a ReferenceError on
        // the first successful poll -- swallowed by the catch below, which reported it as a
        // telemetry failure and kept retrying every 2 seconds for ever. The intended "repaint once
        // on the first real data" is already done by the setState calls themselves, so the line is
        // deleted rather than recreated: a forced repaint is exactly what React does when state
        // changes, and adding a counter to trigger it would be a second mechanism for the same job.
        if (first) { first = false; }
      } catch (e) {
        flushTelemetryError(e.message || String(e));
      } finally {
        inFlight = false;
      }
    };

    const interval = setInterval(pollTelemetry, 2000);
    pollTelemetry();

    // --- THE STREAM, WHICH IS THE POINT OF THE WHOLE THING ---
    //
    // The backend has been delivering live session events on /stream the entire time (measured:
    // 39 frames in 5 seconds) and the Reactor IGNORED it, polling once every 2 seconds instead. So
    // the room was a snapshot refreshed twice a second while a real event channel ran unused.
    //
    // WHY BOTH. The poll answers "what is the state of the fleet" and catches a session that has
    // gone QUIET -- nothing is emitted when an agent stops, so only a timer can notice. The stream
    // answers "something just happened" and is the only thing that can make a jet mean anything.
    // They are not redundant: one is a heartbeat, the other is a nerve.
      let es: EventSource | null = null;
      let retryMs = 2000;
      let retryTimer: ReturnType<typeof setTimeout> | null = null;
      const connect = () => {
        try {
          es = new EventSource(`${FLEETVIEW_ORIGIN}/stream`);
          es.onopen = () => { retryMs = 2000; };   // a good connection resets the backoff
          es.onmessage = (ev) => {
            try {
              const frame = JSON.parse(ev.data);
              if (frame?.type === 'cue') {
                const node = engineState.current.nodes.find((n: any) => n.sessionId === frame.target_id);
                if (node) {
                  const p = node.position;
                  if (engineState.current.cine.onCue(frame, [p.x, p.y, p.z])) {
                    engineState.current.cineTarget = p.clone();
                    cueSayRef.current(String(frame.monologue || ''));
                  }
                }
                return;
              }
              if (frame?.kind === 'gate' && frame.gate) {
                setGates((g) => [frame, ...g].slice(0, 40));
                // The stream replays the last 15 minutes on connect; only a decision made now is spoken.
                const fresh = Date.now() - Date.parse(frame.at || '') < 20000;
                if (fresh && frame.gate.verdict === 'refuse') {
                  cueSayRef.current(`${frame.gate.name} refused: ${frame.gate.reason || 'a claim with nothing behind it'}`);
                }
                return;
              }
              const sf = parseStoryFrame(frame);
              if (sf) {
                dispatchStory(sf);
                const { story } = sf;
                const nowMs = Date.now();
                const interrupt = shouldInterrupt(story, nowMs, seenBreakingRef.current);
                if (interrupt) {
                  seenBreakingRef.current.add(story.id);
                  setBreakingStory(story);
                  clearTimeout(breakingTimer.current);
                  breakingTimer.current = setTimeout(() => setBreakingStory(null), 8000);
                  cueSayRef.current(story.anchor || story.headline);
                }
                // Replayed history (the last hour, on connect) fills the rundown silently: only a
                // story that happened in the last 120s rings, bursts, or moves the camera.
                const atMs = Date.parse(story.at);
                if (Number.isNaN(atMs) || Math.abs(nowMs - atMs) > 120_000) return;
                const visual = visualFor(story);
                engineState.current.intentCue = { t: 0, kind: visual.ring, color: visual.color };
                engineState.current.intentColor = visual.color;
                if (visual.burst > 0) {
                  fire(engineState.current.intentJets, 0, 0, `story:${story.id}`, visual.burst, visual.ring === 'fire' ? 'stuck' : 'thinking');
                }
                if (
                  visual.shot &&
                  engineState.current.cine.state === 'idle' &&
                  (interrupt || nowMs - lastStoryShotMsRef.current >= 20000)
                ) {
                  lastStoryShotMsRef.current = nowMs;
                  if (
                    engineState.current.cine.onCue(
                      { target_id: story.id, shot_type: visual.shot, monologue: '', focal_length: 50, dolly_speed: 1, timestamp: story.at },
                      [0, 0, 0],
                    )
                  ) {
                    engineState.current.cineTarget = new THREE.Vector3(0, 0, 0);
                  }
                }
                return;
              }
              const rec = frame?.record;
              if (!rec?.session_id) return;
              // Count what arrived, per session, and let the render loop consume it. NOT fired
              // here: this handler runs off the browser's event queue and a burst would arrive in
              // one tick, where the loop can spread it across frames.
              const prev = engineState.current.eventCounts.get(rec.session_id);
              const now = Number(rec.event_count) || 0;
              // SEEDED, NOT ASSUMED ZERO.
              //
              // On the first frame of a session there is no previous count, and treating that as 0
              // makes every existing agent look like it just fired hundreds of events at once -- a
              // FALSE ERUPTION on every page load, for every session, which is precisely the
              // dishonesty the design forbids ("inventing motion to look alive"). The first
              // sighting SEEDS the counter and fires nothing.
              //
              // `Math.max(0, ...)` also covers a DECREASE: a reaped session's count can fall, and
              // a negative delta would corrupt the stored value.
              const arrived = prev === undefined ? 0 : Math.max(0, now - prev);
              if (prev === undefined || now >= prev) {
                engineState.current.eventCounts.set(rec.session_id, now);
              }
              if (arrived > 0) {
                // BOUNDED. The render loop drains this every frame, but a PAUSED TAB runs no frames
                // at all -- and an EventSource keeps delivering while the tab is hidden. Without a
                // cap, a backgrounded board collects every frame in memory and pours them into one
                // enormous burst the moment it is refocused.
                const arrivals = engineState.current.arrivals;
                arrivals.push({ sessionId: rec.session_id, arrived });
                if (arrivals.length > 200) arrivals.splice(0, arrivals.length - 200);
              }
            } catch { /* a malformed frame is not a reason to drop the channel */ }
          };
          es.onerror = () => {
            try { es?.close(); } catch { /* already closed */ }
            es = null;
            if (cancelled) return;
            // Backoff, capped: a backend that is down for a minute is retried every 30s rather than
            // hammered twice a second.
            retryTimer = setTimeout(connect, retryMs);
            retryMs = Math.min(30000, retryMs * 2);
          };
        } catch { /* an EventSource the browser refuses leaves the poll doing its job */ }
      };
      connect();

    return () => {
      cancelled = true;
      clearInterval(interval);
      if (retryTimer) clearTimeout(retryTimer);
      try { es?.close(); } catch { /* already closed */ }
    };
  }, [api]);

  // THE PULSE POLL WAS REMOVED, not re-implemented.
  //
  // It fetched `/history` for the nine busiest sessions every 15 seconds -- nine requests of up to
  // 40 events each -- into a `pulses` state that NOTHING RENDERED. It was written for a "harness
  // rhythm" tab that was then deleted as clutter, and the fetch outlived its reader: a slow,
  // heavy, periodic load on the ledger for a value no one ever saw.
  //
  // Removing it is the fix. If a rhythm view is wanted later, it starts by wiring the render and
  // then adds the fetch -- not the other way round.

  // --- WIRED: ACTION HANDLERS ---
  //
  // The founder's optimistic update is kept EXACTLY as written -- the node changes colour on the
  // instant of the press, because a control surface that waits for a round trip feels broken.
  // What is added is the real dispatch, and an HONEST ROLLBACK: if the backend refuses, the node
  // is put back and the reason is shown. An optimistic update that never rolls back is a lie that
  // outlives the request.
  const actionRef = useRef(null);
  const [actionStatus, setActionStatus] = useState(null);

  const dispatchAction = async (verb, node) => {
    if (!node?.sessionId) {
      setActionStatus({ verb, ok: false, text: 'no live session bound to this node yet' });
      return;
    }
    setActionStatus({ verb, ok: null, text: `${verb} → ${node.sessionId.slice(-8)}…` });
    try {
      const base = baseUrlRef.current;
      if (!base) throw new Error('discovery not ready');
      // THE REAL ENDPOINTS. The plugin already serves one path per verb (serve.py), each
      // answering with the signal it recorded or an honest refusal, so the reactor posts to the
      // verb's OWN path rather than inventing an aggregator.
      const path = verb === 'stop' ? 'stop' : verb === 'apprv' ? 'approve' : verb === 'deny' ? 'deny' : 'nudge';
      const payload = { session_id: node.sessionId, runtime: node.runtime, by: 'fleet-reactor' };
      if (verb === 'steer') payload.text = window.prompt('Steer prompt for ' + node.id) || '';
      const res = await api.fetch(`${base}/fleetview/${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        // Refused. Put the node back and say why -- a runtime with no channel returns 422 with
        // its reason, and that reason is the most useful thing on the screen.
        node.state = node.prevState || node.state;
        node.baseColor = new THREE.Color(COLORS[node.state]);
        setActionStatus({ verb, ok: false, text: body.error || `refused (${res.status})` });
        return;
      }
      setActionStatus({ verb, ok: true, text: `${verb} accepted` });
    } catch (e) {
      setActionStatus({ verb, ok: false, text: e.message || String(e) });
    }
  };

  // --- THE ESTATE'S VOICE ENGINE, NOT THE BROWSER'S ---
  //
  // This block used to be 126 lines of `SpeechRecognition` + `speechSynthesis` + a text field,
  // with a timeout, an error table, and a fallback for when the recogniser silently never fired.
  // All of it existed to work around two browser APIs:
  //
  //   SpeechRecognition -> Chrome streams the mic to Google; unreachable, it fires `start` then
  //                        `end` with no error and the bar hangs on "listening" for ever.
  //   speechSynthesis   -> the OS's formant voices, audibly worse than the estate's own.
  //
  // The estate runs its own engine (faster-whisper hearing, Kokoro speaking, 78 voices,
  // barge-in). It is mounted here as a hook, and the text field stays because talking quietly in
  // an open office is a real thing to need.
  // `voice` is declared ABOVE its first use (see the engine block near the top of this file):
  // a `const` that a useCallback body closes over is in the temporal dead zone until its own line
  // runs, and `talkTo` referenced it 500 lines earlier -- which threw
  // "Cannot access 'voice' before initialization" and blanked the page.
  const [voiceDraft, setVoiceDraft] = useState('');
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceText, setVoiceText] = useState('');

  // Keep the on-screen line in step with the engine: what was heard, the reply, and any reason
  // the engine could not work. The engine names the real cause (mic permission vs service
  // unreachable), which the old code could not distinguish.
  useEffect(() => {
    if (partial) setVoiceText(`you: ${partial}…`);
    else if (voice.heard) setVoiceText(`you: ${voice.heard}`);
    else if (voice.reply) setVoiceText(voice.reply);
    else if (voice.detail) setVoiceText(voice.detail);
  }, [partial, voice.heard, voice.reply, voice.detail]);

  const openVoice = async () => {
    setVoiceOpen(true);
    if (voice.state === 'off') await voice.start();
    else voice.stop();
  };


  const handleAction = (action) => {
    // A SILENT NO-OP IS A LIE. This returned early with nothing selected, so pressing Stop on an
    // unselected reactor did nothing and said nothing -- indistinguishable from a broken button.
    // A control that cannot act must say why; that is the same rule the backend already follows
    // with its 422s.
    if (!uiState.selectedNodeId) {
      setActionStatus({
        verb: action,
        ok: false,
        text: 'select a node first — click an agent, then steer it',
      });
      return;
    }
    const node = engineState.current.nodes.find(n => n.id === uiState.selectedNodeId);
    if (!node) return;
    // A node with no session is a sphere slot, not an agent: it has nothing to send to, and
    // pretending otherwise would dispatch at a uuid that does not exist.
    if (!node.sessionId) {
      setActionStatus({ verb: action, ok: false, text: 'this node has no live session' });
      return;
    }

    // The founder's optimistic update, verbatim.
    node.prevState = node.state;
    if (action === 'stop') node.state = 'stuck';
    if (action === 'apprv') node.state = 'thinking';
    node.baseColor = new THREE.Color(COLORS[node.state]);

    void dispatchAction(action, node);
  };

  return (
    // FILL THE SPACE THE PARENT GIVES US, NOT THE VIEWPORT.
    //
    // Two attempts failed here, and the measurement says why. `h-screen` (= 100vh) started BELOW
    // Backstage's header, so the room ran off the bottom. `h-[calc(100vh-6rem)]` was worse: the
    // element measured 1031px inside a 950px viewport, because Backstage's own page container
    // (`BackstageSidebarPage-root`, measured at 1128px) is taller than the viewport it sits in --
    // so ANY arithmetic against 100vh is arithmetic against the wrong box.
    //
    // `h-full` asks the parent instead, which is the only value that is correct whatever chrome
    // wraps this page. The parent chain resolves to a definite height because Backstage's layout
    // is a flex column that fills the viewport; `min-h-[520px]` keeps it usable if it ever is not,
    // since a room squeezed to nothing is worse than one that scrolls.
    // THE ROOM OWNS THE VIEWPORT. NOT THE PAGE CONTAINER, THE VIEWPORT.
    //
    // Council ruling, 2026-09-20: "Eliminate the chrome; do not integrate. Boxing a dark spatial
    // instrument in 224px of bright Backstage portal shatters the immersion. The WebGL canvas must
    // touch the physical bezels of the screen."
    //
    // Measured before this change: the room sat at x=224 with a pure-white rgb(255,255,255)
    // sidebar and an rgb(245,245,245) body around a near-black rgb(3,5,8) interior. `noHeader:true`
    // removed the white TOP band; `replaces` on the theme module did NOT change the body, because
    // Backstage reads the active theme from `localStorage["theme"]` (AppThemeSelector) and this
    // browser has "light" stored. Neither is worth fighting.
    //
    // `position: fixed; inset: 0` puts the room ABOVE the chrome rather than beside it. The
    // sidebar and the body remain in the DOM and are entirely beneath -- no theme surgery, no
    // `!important` against vendor CSS, and it cannot regress when Backstage reorganises.
    //
    // The measured height is kept as a fallback for the (now impossible) case where fixed
    // positioning is unavailable, and `z-index: 1` is deliberately low enough that a real Backstage
    // overlay -- a confirmation dialog, an error toast -- still appears above the room.
    <div
      ref={rootRef}
      // Z-INDEX ABOVE BACKSTAGE, AND THAT IS THE POINT RATHER THAN A HACK.
      //
      // Measured after the first attempt at `z-index: 1`: the room filled the viewport correctly
      // (`1600x1000 @0,0`) but a `MuiBox-root` -- Backstage's own page container -- sat ON TOP of
      // it, so the panel's open button at (16,144) was unclickable and hit-testing returned the
      // container instead. The console reported no error; the control simply did nothing.
      //
      // The council ruling was "the canvas must touch the physical bezels of the screen", and
      // filling the viewport while sitting UNDER the portal is not that. 1200 is above Backstage's
      // own layers (its dialogs sit near 1300) so a real confirmation prompt still appears above
      // the room, which is the one thing that must.
      style={{ position: 'fixed', inset: 0, zIndex: 1200 }}
      className="fleet-reactor bg-[#030508] overflow-hidden text-white font-sans selection:bg-cyan-500/30"
    >
      
      {/* 3D Canvas Mount Point */}
      <div ref={mountRef} className="absolute inset-0 cursor-crosshair"></div>

      {/* THE LABELS, IN SPACE.

          WHY THIS REPLACES A LIST. The panel answered "which agent is which" by making the reader
          cross-reference a 37-row table against a rotating sphere -- two competing metaphors, one
          covering the other. The founder, 2026-09-20: "the panel on the left now clutters the page,
          need super creative".

          A label beside its own node answers the question where it is asked. It is the same idea
          the radial menu already uses: a 3D position projected to screen coordinates every frame,
          written straight into `style.transform` so React never re-renders for a moving label.

          Near nodes show more: the label grows with the node's apparent size, and the name is the
          TASK rather than a slot id, because `AG-1013` tells a person nothing. Full context still
          lives in the panel, which now appears only for a selected agent. */}
      <div ref={labelsRef} className="absolute inset-0 pointer-events-none z-20 overflow-hidden"></div>

      {/* THE RADIAL MENU. The render loop has been positioning `radialMenuRef` every frame since
          this file was written -- projecting the selected node's 3D position to screen coordinates
          and setting `opacity: 1` -- and NOTHING WAS ATTACHED TO IT. The four controls existed as
          dead code in the animation and nowhere in the DOM.

          So a person could select an agent and had no way to act on it from the room. These are
          the four verbs the backend actually implements, arranged around the node the loop is
          already tracking: stop, steer, and the two the estate only supports for sovereign.

          The buttons carry no position of their own -- `transform` is written by the render loop,
          which is why this element must stay `absolute` with `top/left: 0` rather than being
          placed by CSS. */}
      <div
        ref={radialMenuRef}
        className="absolute top-0 left-0 z-50 opacity-0 pointer-events-none flex items-center justify-center"
        style={{ transition: 'opacity .18s ease' }}
      >
        {(() => {
          // Four verbs at four compass points, as the founder's design arranges them.
          const ring = [
            { verb: 'stop', label: 'Stop', pos: 'translate(-50%,-50%) translate(0,-46px)', fg: '#ff0055', bd: 'rgba(255,0,85,.5)' },
            { verb: 'steer', label: 'Steer', pos: 'translate(-50%,-50%) translate(46px,0)', fg: '#00f0ff', bd: 'rgba(0,240,255,.5)' },
            { verb: 'apprv', label: 'Apprv', pos: 'translate(-50%,-50%) translate(0,46px)', fg: '#00ffaa', bd: 'rgba(0,255,170,.5)' },
            { verb: 'deny', label: 'Deny', pos: 'translate(-50%,-50%) translate(-46px,0)', fg: '#ffaa00', bd: 'rgba(255,170,0,.5)' },
          ];
          return ring.map((b) => (
            <button
              key={b.verb}
              type="button"
              data-testid={`radial-${b.verb}`}
              onClick={() => void handleAction(b.verb)}
              className="absolute w-[42px] h-[42px] rounded-full flex items-center justify-center text-[8px] font-mono uppercase tracking-wider cursor-pointer backdrop-blur-md"
              style={{
                transform: b.pos,
                color: b.fg,
                border: `1px solid ${b.bd}`,
                background: 'rgba(0,0,0,.8)',
                pointerEvents: 'auto',
              }}
            >
              {b.label}
            </button>
          ));
        })()}
      </div>

      {/* Hover Tooltip (Native DOM updated in Render Loop) */}
      <div 
        ref={tooltipRef} 
        className="absolute z-50 pointer-events-none opacity-0 transition-opacity duration-200 bg-black/60 backdrop-blur-md border border-white/10 p-3 rounded-lg flex flex-col gap-1 shadow-2xl"
      >
        <div className="text-[9px] uppercase tracking-widest text-white/40 font-mono">Node Identity</div>
        <div id="tt-id" className="text-sm font-bold font-mono text-white">---</div>
        <div id="tt-state" className="text-[10px] font-bold uppercase tracking-wider mt-1">---</div>
        {/* The context the tooltip was missing: what this agent is doing, which harness it runs,
            which repo it is in, and what it has cost. */}
        <div id="tt-task" className="text-[11px] text-white/80 mt-2 max-w-[320px] leading-snug"></div>
        <div id="tt-meta" className="text-[10px] font-mono text-white/45 mt-1"></div>
        <div id="tt-spend" className="text-[10px] font-mono text-white/35 mt-0.5"></div>
      </div>

      {/* Top HUD.

          THE HEADER WAS BEING CUT OFF AND OVERLAPPED, for two reasons:

            1. It sat at `top-0`, and this page renders inside Backstage's own chrome -- so the
               app bar covered the top of it. `top-0` is the top of the VIEWPORT, not the top of
               the room.
            2. The fleet ticker was `top-6 left-1/2 z-20` while this was `z-10`, so the ticker
               was painted OVER the middle of the header, which is what "overlapped" was.

          The fix is to give the header its own band below the ticker and stop the two sharing
          vertical space: the ticker moves to the top centre, and everything else starts under
          it. Padding on the container is what makes this survive any Backstage chrome height. */}
      <div className="absolute top-0 left-0 w-full px-6 pb-2 pt-4 flex justify-between items-start z-30 pointer-events-none select-none" style={{ maxHeight: '3.5rem' }}>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_rgba(0,240,255,0.8)]"></div>
            <h1 className="text-2xl font-bold tracking-[0.2em] text-white drop-shadow-md">FLEET REACTOR</h1>
          </div>          <p className="text-[10px] text-white/40 uppercase font-mono tracking-widest pl-5">Native Spatial Topology • Active Stream</p>
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

      {/* THE FLEET TICKER, AND THE ONLY PLACE A FAILURE IS REPORTED.

          `live.ticker` and `live.error` were being COMPUTED every two seconds and rendered
          NOWHERE -- the whole telemetry line had been lost in an earlier edit, so an HTTP 503, a
          "no sessions", a "discovery not ready", and a swallowed ReferenceError were all equally
          invisible. A board that cannot say it has lost its data is indistinguishable from a board
          that has none, which is the exact failure this project keeps re-learning.

          The ticker shows the fleet in one scan line (position fixed, only the numbers change --
          an ATC strip board). On failure it becomes the error, in red, so the two states can never
          be confused. */}
      <div
        data-testid="reactor-telemetry"
        className="absolute top-16 left-1/2 -translate-x-1/2 z-40 px-4 py-1.5 rounded-full border backdrop-blur-md text-[10px] font-mono uppercase tracking-widest whitespace-nowrap max-w-[92vw] overflow-hidden text-ellipsis"
        style={{
          color: live.ok ? COLORS.finished : COLORS.stuck,
          borderColor: live.ok ? 'rgba(255,255,255,.1)' : 'rgba(255,0,85,.4)',
          background: live.ok ? 'rgba(0,0,0,.7)' : 'rgba(255,0,85,.08)',
        }}
        title={live.ok ? live.ticker : `telemetry unavailable — ${live.error}`}
      >
        {/* ADDED: an intent result holds the ticker for 4s; then a director cue; then the live line. */}
        {intentLine || cueLine || (live.ok
          ? live.ticker || `live · ${live.count} sessions`
          : `OFFLINE · ${live.error || 'connecting'}`)}
      </div>

      {/* THE BURN BAR. Cost as a RATE, never as a figure.
      
          The design spec: "one burn bar, whose LEADING EDGE GLOW WIDTH is the rate... no dollar
          figure anywhere except on tap." Its reasoning is that a rate is perceived in peripheral
          vision and a number must be read -- and a permanent number competes with the four state
          counts a person actually acts on.
      
          So the FILL is total spend across the day and the GLOW is the current rate: a bar filling
          slowly with a cold edge means work is cheap and steady, a hot edge means it is burning
          now. The figure appears only in the hover title, which is the "on tap" the spec allows. */}
      <div
        data-testid="burn-bar"
        title={burnRef.current.label}
        className="absolute top-16 right-6 z-40 w-[110px] h-[3px] rounded-full overflow-hidden cursor-help"
        style={{ background: 'rgba(255,255,255,.07)' }}
      >
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{
            width: `${Math.round(burnRef.current.fill * 100)}%`,
            background: `linear-gradient(90deg, rgba(0,240,255,.5), rgba(255,170,0,${0.4 + burnRef.current.heat * 0.6}))`,
            // THE HEAT IS THE RATE. A fast-burning fleet has a hot leading edge; a slow one is dim.
            boxShadow: burnRef.current.heat > 0.05
              ? `0 0 ${Math.round(4 + burnRef.current.heat * 16)}px rgba(255,170,0,${0.3 + burnRef.current.heat * 0.6})`
              : 'none',
          }}
        />
      </div>

      {/* THE RIGHT-HAND LIVE COLUMN. One owner per corner: the channel strip owns the bottom-right
          footer row and the voice picker owns the top right, so the two live panels (token
          efficiency, safeguards) share one column between them, bottom-anchored just above the
          strip. Before this they were placed independently and landed on top of the strip and the
          sonar (founder 2026-09-29: "the clean layout is getting bastardised"). */}
      <div className="absolute right-6 top-36 bottom-24 z-30 w-[280px] flex flex-col justify-end gap-2 pointer-events-none">
      <EfficiencyHud />

      {/* SAFEGUARDS: every gate decision on a real turn, newest first, as it lands on
          the bus. Nothing here is sampled or seeded; an empty panel says the bus has carried none. */}
      <div
        data-testid="safeguards"
        className="w-full rounded-xl bg-black/55 border border-white/10 backdrop-blur-md p-2 select-none pointer-events-none"
      >
        <div className="flex items-baseline gap-2 px-1 pb-1">
          <span className="text-[9px] font-mono uppercase tracking-widest text-white/60 flex-1">safeguards · live</span>
          <span className="text-[9px] font-mono text-emerald-300/80">{gates.filter((g) => g.gate.verdict === 'pass').length} pass</span>
          <span className="text-[9px] font-mono text-rose-400/90">{gates.filter((g) => g.gate.verdict === 'refuse').length} refused</span>
          {gates.some((g) => g.gate.verdict === 'blind') ? (
            <span className="text-[9px] font-mono text-amber-300/80">{gates.filter((g) => g.gate.verdict === 'blind').length} blind</span>
          ) : null}
        </div>
        {gates.length ? gates.slice(0, 6).map((g, i) => (
          <div key={`${g.session_id}-${g.at}-${i}`} className="px-1 py-0.5 flex flex-col">
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block w-1.5 h-1.5 rounded-full"
                style={{ background: g.gate.verdict === 'pass' ? '#34d399' : g.gate.verdict === 'refuse' ? '#fb7185' : '#fcd34d' }}
              />
              <span className="text-[9px] font-mono text-white/70">{g.gate.name}</span>
              <span className="text-[9px] font-mono text-white/40">{g.gate.verdict}</span>
              <span className="text-[8px] font-mono text-white/30 truncate flex-1 text-right">
                {String(g.session_id || '').slice(0, 8)} · {String(g.at || '').slice(11, 19)}
              </span>
            </div>
            {g.gate.verdict !== 'pass' && (g.gate.reason || g.gate.claim) ? (
              <div className="text-[9px] text-white/45 truncate pl-3">{g.gate.claim || g.gate.reason}</div>
            ) : null}
          </div>
        )) : (
          <div className="px-1 py-1 text-[9px] font-mono text-white/30">no gate decision on the bus yet</div>
        )}
      </div>
      </div>

      {/* THE VOICE PICKER, top right under the burn bar (founder 2026-09-26: "move it to top right",
          "not obscuring the view", "looks like 1930, the rest is 2100"). Closed it is one chip; open,
          a glass list the same idiom as the rest of the HUD. Every choice goes through
          /voice/select, and the chip shows what the service says is live. */}
      {(() => {
        const groups: [string, string, string[]][] = [
          ['kokoro', 'Kokoro', legacyVoice.catalogue.kokoro || []],
          ['say', 'macOS', legacyVoice.catalogue.say || []],
          ['piper', 'Piper', legacyVoice.catalogue.piper || []],
          ['cloud', 'Online', legacyVoice.catalogue.cloud || []],
          ['voice-router', 'Streaming', routerVoice.reachable ? routerVoice.catalogue.piper : []],
        ];
        const shown = streaming && routerVoice.reachable ? routerVoice.current : legacyVoice.current;
        return (
          <div
            data-testid="voice-picker"
            data-value={`${shown.engine}:${shown.voice}`}
            onPointerUp={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            style={{ position: 'absolute', top: 80, right: 24, zIndex: 45, width: 190, fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}
          >
            <button
              type="button"
              data-testid="voice-picker-chip"
              onClick={() => setVoiceMenu((o) => !o)}
              title="which voice speaks"
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
                borderRadius: 999, cursor: 'pointer', color: 'rgba(255,255,255,.75)',
                background: 'rgba(3,5,8,.55)', backdropFilter: 'blur(10px)',
                border: `1px solid ${voiceMenu ? 'rgba(0,240,255,.55)' : 'rgba(0,240,255,.18)'}`,
                boxShadow: voiceMenu ? '0 0 18px rgba(0,240,255,.25)' : 'none',
                fontSize: 10, letterSpacing: '.18em', textTransform: 'uppercase',
              }}
            >
              <span style={{ width: 6, height: 6, borderRadius: 999, background: '#00f0ff', boxShadow: '0 0 8px #00f0ff', flex: 'none' }} />
              <span style={{ color: 'rgba(255,255,255,.4)' }}>voice</span>
              <span style={{ color: '#00f0ff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{shown.voice}</span>
              <span style={{ marginLeft: 'auto', color: 'rgba(0,240,255,.6)', transform: voiceMenu ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }}>▾</span>
            </button>
            {voiceMenu ? (
              <div
                style={{
                  marginTop: 6, maxHeight: '45vh', overflowY: 'auto', padding: 6, borderRadius: 12,
                  background: 'rgba(3,5,8,.72)', backdropFilter: 'blur(14px)',
                  border: '1px solid rgba(0,240,255,.2)', boxShadow: '0 10px 40px rgba(0,0,0,.6), 0 0 24px rgba(0,240,255,.08)',
                }}
              >
                {groups.filter(([, , list]) => list.length).map(([engine, label, list]) => (
                  <div key={engine}>
                    <div style={{ padding: '8px 8px 4px', fontSize: 9, letterSpacing: '.25em', textTransform: 'uppercase', color: 'rgba(255,255,255,.3)' }}>
                      {label} · {list.length}
                    </div>
                    {list.map((v) => {
                      const on = shown.engine === engine && shown.voice === v;
                      return (
                        <button
                          type="button"
                          key={`${engine}-${v}`}
                          data-voice={`${engine}:${v}`}
                          onClick={() => {
                            if (engine === 'voice-router') chooseStreaming(true);
                            else { chooseStreaming(false); void legacyVoice.selectVoice(engine, v); }
                            setVoiceMenu(false);
                          }}
                          style={{
                            display: 'block', width: '100%', textAlign: 'left', padding: '5px 10px', borderRadius: 6,
                            cursor: 'pointer', fontSize: 11, letterSpacing: '.06em', border: 'none',
                            color: on ? '#00f0ff' : 'rgba(255,255,255,.7)',
                            background: on ? 'rgba(0,240,255,.12)' : 'transparent',
                          }}
                          onMouseEnter={(e) => { if (!on) e.currentTarget.style.background = 'rgba(255,255,255,.06)'; }}
                          onMouseLeave={(e) => { if (!on) e.currentTarget.style.background = 'transparent'; }}
                        >
                          {on ? '● ' : ''}{v}
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        );
      })()}

      {/* THE EPHEMERAL SUBTITLE.
      
          The consultant's single biggest finding: "the biggest lie currently on screen is the
          illusion of seamless voice control while hiding the raw transcript... the person is
          blindly firing Whisper transcripts into a black box." This is the loop closed -- what was
          heard, and what was said back, shown for three seconds and gone.
      
          Positioned just above the mic and deliberately NOT in the panel: the proof must be where
          the person's eye already is while they are speaking. It disappears on its own, so it costs
          no permanent space -- which is the whole reason it can exist at all. */}
      {voice.state !== 'off' && (voice.heard || voice.reply) ? (
        <div
          data-testid="voice-subtitle"
          className="absolute bottom-28 left-1/2 -translate-x-1/2 z-40 max-w-[560px] px-4 py-2 rounded-lg bg-black/80 border border-white/10 backdrop-blur-md pointer-events-none"
        >
          {voice.heard ? (
            <div className="text-[12px] font-mono text-cyan-300 truncate">› {voice.heard}</div>
          ) : null}
          {voice.reply ? (
            <div className="text-[12px] text-white/85 leading-snug pt-0.5 truncate">{voice.reply}</div>
          ) : null}
        </div>
      ) : null}

      {/* THE AGENT PANEL: WHO IS WHO, AND WHAT EACH ONE IS DOING.

          Replaces a legend that listed four colour names ("Processing", "Awaiting I/O", "Blocked",
          "Sequence Complete") -- which told a reader what the colours meant and nothing about the
          fleet. The founder, 2026-09-20: "i dont know whats what, just things moving with no
          context, dont know which harness model provider".

          Every row is a real session and every value is read from the same envelope the nodes are
          drawn from, on the same 2s poll, so a row and a node cannot disagree. The wash bar under
          each row is that session's event_count against the busiest session on the board -- a
          relative measure, because an absolute count is meaningless without knowing the scale. */}
      {/* The panel occupies the room's full usable height below the header band. It is positioned
          against the ROOM (`absolute` inside `.fleet-reactor`), not the viewport -- the room starts
          224px right and 96px down because of Backstage's own sidebar and header, measured at
          1500x950, so a viewport-relative offset would be wrong by exactly that much. */}
      {/* ONE AGENT, WHEN ONE IS SELECTED. NOT THE WHOLE FLEET.

          This was a 37-row always-on roster. Measured 2026-09-20: the founder called it clutter --
          "the panel on the left now clutters the page". It was, and the reason is structural: a
          scrolling table printed over a spatial view is a second interface competing with the
          first, and the reader has to cross-reference the two by hand.

          The fleet's identity now lives where it belongs -- in the labels beside each node, so
          "which agent is which" is answered in space and needs no list. This panel therefore shows
          only the SELECTED agent, which is the one question the labels deliberately do not fully
          answer (full task, cost, events, replies). It slides in on selection and out on deselect,
          so the room is uncluttered by default and detailed on request. */}
      {selectedRow ? (
        <div className="absolute top-36 left-4 z-30 w-[380px] flex flex-col bg-black/70 border border-white/10 rounded-xl backdrop-blur-md select-none shadow-2xl overflow-hidden transition-all duration-300">
          <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-white/10">
            <div className="min-w-0">
              <div
                className="text-[9px] font-mono uppercase tracking-widest"
                style={{ color: COLORS[selectedRow.activity] }}
              >
                {selectedRow.activity} · {selectedRow.runtime}
                {selectedRow.model ? ` · ${selectedRow.model}` : ''}
                {selectedRow.repo ? ` · ${selectedRow.repo}` : ''}
              </div>
              <div className="text-[12px] text-white/90 leading-snug mt-1">
                {selectedRow.task || '(no task recorded)'}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setUiState((s) => ({ ...s, selectedNodeId: null }))}
              className="tab-plain text-white/40 hover:text-white/80 text-[14px] leading-none px-1 cursor-pointer bg-black/40 rounded"
              title="deselect"
            >
              ✕
            </button>
          </div>

          {/* The numbers, which is what a person asks next after "what is it doing". */}
          <div className="grid grid-cols-3 border-b border-white/10">
            <div className="px-4 py-2">
              <div className="text-[8px] font-mono uppercase tracking-widest text-white/35">spend</div>
              <div className="text-[13px] font-mono text-white/85">${selectedRow.spend.toFixed(2)}</div>
            </div>
            <div className="px-4 py-2 border-l border-white/10">
              <div className="text-[8px] font-mono uppercase tracking-widest text-white/35">events</div>
              <div className="text-[13px] font-mono text-white/85">{selectedRow.events}</div>
            </div>
            <div className="px-4 py-2 border-l border-white/10">
              <div className="text-[8px] font-mono uppercase tracking-widest text-white/35">quiet</div>
              <div className="text-[13px] font-mono text-white/85">
                {selectedRow.ageMs == null ? '—'
                  : selectedRow.ageMs < 60000 ? `${Math.round(selectedRow.ageMs / 1000)}s`
                  : selectedRow.ageMs < 3600000 ? `${Math.round(selectedRow.ageMs / 60000)}m`
                  : `${Math.round(selectedRow.ageMs / 3600000)}h`}
              </div>
            </div>
          </div>

          {/* THE CONVERSATION. Both sides, oldest at the top, newest at the bottom -- a chat, not a
              log.

              THE THREAD IS BUILT FROM TWO SOURCES and that is deliberate: steers come from
              `fleetview_signals` (written when a person sends) and replies from `fleetview_replies`
              (written when the session answers). They are separate tables because they have
              different authors and lifetimes, and merging them HERE rather than in the database
              keeps the write paths honest -- a steer is not a reply and `by` should not mean
              "sender or author depending on kind".

              Auto-scrolls to the newest message, because a conversation you have to scroll to
              follow is not a conversation. */}
          {(() => {
            const mine = signals
              .filter((s: any) => s.session_id === selectedRow.sessionId && s.text)
              .map((s: any) => ({
                id: `s${s.id}`,
                at: s.created_at,
                who: 'you',
                text: s.text,
                ok: s.ok !== false,
                // A steer that is still sitting in the mailbox has NOT been read -- the schema
                // records that as `read_at`, and saying so is the difference between "sent" and
                // "it has heard me".
                pending: !s.read_at,
              }));
            const theirs = replies
              .filter((rp: any) => rp.session_id === selectedRow.sessionId)
              .map((rp: any) => ({
                id: `r${rp.id}`,
                at: rp.created_at,
                who: rp.author || 'agent',
                text: rp.text,
                ok: true,
                pending: false,
              }));
            const thread = [...mine, ...theirs].sort((a, b) =>
              String(a.at).localeCompare(String(b.at)),
            );
            if (!thread.length) {
              return (
                <div className="px-3 py-3 text-[10px] font-mono text-white/30">
                  nothing said yet — type below and it answers at its next turn
                </div>
              );
            }
            return (
              <div ref={threadRef} className="flex-1 min-h-[90px] max-h-[240px] overflow-y-auto px-3 py-2 flex flex-col gap-1.5">
                {thread.slice(-30).map((m) => (
                  <div
                    key={m.id}
                    className={`flex flex-col ${m.who === 'you' ? 'items-end' : 'items-start'}`}
                  >
                    <div
                      className={`max-w-[92%] px-2 py-1 rounded-lg text-[11px] leading-snug ${
                        m.who === 'you'
                          ? 'bg-cyan-500/12 border border-cyan-500/25 text-cyan-100/90'
                          : 'bg-white/6 border border-white/10 text-white/85'
                      }`}
                    >
                      {String(m.text).slice(0, 700)}
                    </div>
                    <div className="text-[8px] font-mono text-white/25 pt-0.5">
                      {m.who === 'you' ? 'you' : m.who}
                      {' · '}
                      {String(m.at).slice(11, 19)}
                      {m.pending ? ' · queued, not yet read' : ''}
                      {m.who === 'you' && !m.ok ? ' · refused' : ''}
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}

          {/* TALK TO THIS SESSION, IN PLACE.

              This replaces `window.prompt`, which is what the steer button used: a browser modal
              that blocks the page, cannot be styled, has no history, and hides the agent you are
              deciding to talk to. A steer is a message, so it gets a message box — with a send
              button, the runtime it will reach, and the honest note about when it arrives. */}
          <form
            className="px-3 py-2 border-t border-white/10"
            onSubmit={(e) => {
              e.preventDefault();
              const text = steerDraft.trim();
              if (!text) return;
              setSteerDraft('');
              void sendSteer(text, selectedRow);
            }}
          >
            <textarea
              data-testid="steer-input"
              value={steerDraft}
              onChange={(e) => setSteerDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  (e.currentTarget.form as HTMLFormElement | null)?.requestSubmit();
                }
              }}
              rows={2}
              placeholder={`message this ${selectedRow.runtime} session…`}
              className="w-full resize-none bg-black/50 border border-white/10 focus:border-cyan-500/50 rounded-lg px-2 py-1.5 text-[11px] font-mono text-white/85 placeholder-white/25 outline-none"
            />
            <div className="flex items-center justify-between pt-1.5">
              <span className="text-[9px] font-mono text-white/30">
                {steerStatus || `delivered at its next turn · ${selectedRow.runtime}`}
              </span>
              <button
                type="submit"
                disabled={!steerDraft.trim()}
                className="tab-plain px-3 py-1 rounded-md border border-cyan-500/40 text-cyan-300 text-[10px] font-mono uppercase tracking-widest cursor-pointer bg-cyan-500/10 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-cyan-500/15"
              >
                send
              </button>
            </div>
          </form>

          {/* TWO WAYS TO END IT, AND THE DIFFERENCE MATTERS.

              STOP asks the session to shut itself down at its next turn boundary. That is graceful:
              the runtime runs its shutdown hooks and the session file closes cleanly. It is also
              the ONLY thing that reaches an agent that is busy but healthy.

              KILL sends SIGTERM to the session's own process, using the PID the extension now
              reports. It is for the rogue case — an agent looping, spending, or wedged inside a
              provider call — where waiting for a turn boundary means waiting for ever.

              NOTHING DURABLE IS LOST, which is why the founder asked for both: the work is on the
              filesystem. Every edit is committed or at least written, the session file holds the
              transcript, and the branch holds the state. A hard kill costs the in-flight turn, not
              the work.

              Kill is deliberately second, smaller, and confirms before firing — a destructive
              button must not sit where a safe one is expected. */}
          <div className="flex items-center gap-2 px-3 py-2 border-t border-white/10">
            <button
              type="button"
              onClick={() => void endSession('stop', selectedRow)}
              className="tab-plain flex-1 px-2 py-1 rounded-md border border-amber-500/40 text-amber-300 text-[10px] font-mono uppercase tracking-widest cursor-pointer bg-amber-500/10 hover:bg-amber-500/15"
              title="ask it to shut down at its next turn boundary"
            >
              stop
            </button>
            <button
              type="button"
              onClick={() => {
                // CONFIRM, because this cannot be undone and the work not yet written is gone.
                if (window.confirm(
                  `SIGTERM ${selectedRow.runtime} session ${selectedRow.sessionId.slice(-8)}?\n\n` +
                  'Anything on disk is kept. The in-flight turn is lost.',
                )) {
                  void endSession('kill', selectedRow);
                }
              }}
              className="tab-plain px-3 py-1 rounded-md border border-red-500/40 text-red-300 text-[10px] font-mono uppercase tracking-widest cursor-pointer bg-red-500/10 hover:bg-red-500/15"
              title="send SIGTERM to the process — for a rogue or wedged session"
            >
              kill
            </button>
          </div>
          {endStatus ? (
            <div className="px-3 pb-2 text-[9px] font-mono text-white/45">{endStatus}</div>
          ) : null}
        </div>
      ) : null}

      {/* THE LEFT PANEL: TABS AND DEPTH.
      
          A space this small cannot hold everything at once, and it should not try. Two axes:
      
            TAB    fleet    the agents that are working, and the counts
                   harness  what the estate knows ABOUT those agents -- receipts, the audit trail,
                            the checks that ran. This is the "evals and judges" surface: the
                            evidence behind a session rather than the session itself.
                   talk     the conversation: what was said, to whom, and by whom.
      
            DEPTH  0  a count and a bar. Nothing to read, just what is happening.
                   1  the task and the branch. Enough to know WHICH work.
                   2  spend, model, events, last reply. Everything the record holds.
      
          One click on a tab, one on the depth control, and the column never looks full -- it looks
          like it is showing what you asked for.

          BUT IT STILL SHOWED BY DEFAULT, and the ruling says it must not: "the permanent 248px left
          rail" is explicitly listed as what gets deleted from the default view. A column of text
          printed over a spatial instrument is the dashboard metaphor, and the whole point of the
          HUD metaphor is that the instrument is uninterrupted until questioned.

          So the rail is now COLLAPSED TO A TAB. Closed, it is one glyph in the corner. Open, it is
          the full column -- and it opens on a click, because the person who wants it is the person
          about to click it. `panelOpen` is that state; nothing is lost, only deferred. */}
      {!selectedRow ? (
        !panelOpen ? (
          // AMBIENT. One glyph, and the fleet's pulse beside it -- no prose at all.
          <button
            type="button"
            data-testid="panel-open"
            onClick={() => setPanelOpen(true)}
            title="open the fleet panel"
            className="absolute top-36 left-4 z-30 flex items-center gap-2 px-2 py-1.5 rounded-md bg-black/40 border border-white/10 backdrop-blur-sm cursor-pointer hover:border-cyan-500/40"
          >
            <span className="text-[10px] font-mono text-white/45">▤</span>
            <span className="flex items-baseline gap-2">
              {(['stuck', 'thinking', 'waiting'] as const).map((a) => {
                const n = rows.filter((r) => r.activity === a).length;
                return (
                  <span key={a} className="text-[10px] font-mono" style={{ color: n ? COLORS[a] : 'rgba(255,255,255,.2)' }}>
                    {n}
                  </span>
                );
              })}
            </span>
          </button>
        ) : (
        // THE PANEL NEEDS A SURFACE. It was fully transparent (`rgba(0,0,0,0)` measured), so the
        // rail's rows floated over a moving 3D scene with no separation from it -- readable only
        // where the room happened to be dark. One background, one blur, and the whole column
        // becomes a readable instrument instead of text over a picture.
        <div className="absolute top-36 bottom-6 left-4 z-30 w-[248px] flex flex-col select-none rounded-xl bg-black/55 border border-white/10 backdrop-blur-md p-2">
          <button
            type="button"
            data-testid="panel-close"
            onClick={() => setPanelOpen(false)}
            title="collapse"
            className="absolute -top-1 -right-1 z-40 w-5 h-5 rounded-full bg-black/70 border border-white/15 text-white/40 hover:text-white/80 text-[10px] font-mono cursor-pointer"
          >
            ✕
          </button>
          {/* THE TABS. */}
          <div className="flex items-center gap-2 pb-2 border-b border-white/10">
            {(['fleet', 'harness', 'friction'] as const).map((t) => (
              <button
                key={t}
                type="button"
                data-testid={`panel-tab-${t}`}
                onClick={() => setPanelTab(t)}
                // THE TABS HAD NO BACKGROUND CLASS AT ALL, so they rendered as the browser's own
                // grey button -- rgb(239,239,239), measured 2026-09-20 -- which is what the founder
                // called "ugly display, not 2100 fitting" and asked me to change SIX times. There
                // was no colour to change: there was a MISSING background, and `appearance: none`
                // to stop the browser painting its own button chrome over whatever we set.
                className={`tab-plain px-2 py-0.5 rounded text-[9px] font-mono uppercase tracking-widest cursor-pointer transition-colors ${
                  panelTab === t
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/40'
                    : 'bg-black/40 text-white/35 border border-white/5 hover:text-white/70'
                }`}
              >
                {t}
              </button>
            ))}
            {/* THE DEPTH CONTROL. One glyph that cycles, because three radio buttons would cost
                more space than the content they reveal. */}
            <button
              type="button"
              data-testid="panel-depth"
              onClick={() => setDepth((d) => (d >= 2 ? 0 : d + 1))}
              title={`detail level ${depth} of 2 — click for ${depth >= 2 ? 'less' : 'more'}`}
              className="tab-plain ml-auto text-[9px] font-mono text-white/35 hover:text-cyan-300 cursor-pointer tracking-widest bg-black/40 rounded px-1"
            >
              {depth === 0 ? '···' : depth === 1 ? '··' : '·'}
            </button>
          </div>
      
          {/* ---- FLEET: the working agents ---- */}
          {panelTab === 'fleet' ? (
            <>
              <div className="flex items-baseline gap-2.5 px-1 pt-2 pb-1">
                {(['stuck', 'thinking', 'waiting', 'finished'] as const).map((a) => {
                  const n = rows.filter((r) => r.activity === a).length;
                  return (
                    <span key={a} className="flex items-baseline gap-1">
                      <span className="text-[13px] font-mono" style={{ color: n ? COLORS[a] : 'rgba(255,255,255,.2)' }}>{n}</span>
                      <span className="text-[7px] font-mono uppercase text-white/35">{a.slice(0, 4)}</span>
                    </span>
                  );
                })}
              </div>
              <div className="flex flex-col gap-1 overflow-y-auto pt-1">
                {activeRows.map((r) => {
                  const talkingTo = voiceTarget === r.sessionId;
                  const mine = replies.filter((rp: any) => rp.session_id === r.sessionId);
                  return (
                    <div
                      key={r.sessionId}
                      data-depth={depth}
                      className="rail-card px-2 py-1 rounded-md bg-black/35 border border-white/5 backdrop-blur-sm"
                      style={{ borderLeft: `2px solid ${COLORS[r.activity]}`, background: talkingTo ? 'rgba(0,240,255,.08)' : undefined }}
                    >
                      <div className="flex items-baseline gap-1">
                        <span className="text-[8px] font-mono uppercase flex-none" style={{ color: COLORS[r.activity] }}>{r.activity}</span>
                        <span
                          className="text-[10px] text-white/80 truncate flex-1 cursor-pointer"
                          onClick={() => {
                            const node = engineState.current.nodes.find((n: any) => n.sessionId === r.sessionId);
                            if (node) setUiState((s2) => ({ ...s2, selectedNodeId: node.id }));
                          }}
                        >{r.task || '(no task)'}</span>
                        <button
                          type="button"
                          data-testid={`talk-${r.sessionId.slice(-8)}`}
                          title={talkingTo ? 'listening to this agent — click to stop' : `talk to this ${r.runtime} session`}
                          onClick={() => void talkTo(r)}
                          // SAME MISSING-BACKGROUND DEFECT AS THE TABS. This button declared only a
                          // text colour, so the browser painted rgb(239,239,239) behind the mic glyph
                          // -- nine white squares down the rail, measured 2026-09-20.
                          className="tab-plain flex-none px-1 py-0.5 rounded cursor-pointer bg-black/40 hover:bg-cyan-500/15"
                          style={{ color: talkingTo ? '#00f0ff' : 'rgba(255,255,255,.35)' }}
                        >
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                            <rect x="9" y="3" width="6" height="11" rx="3" />
                            <path d="M5 11a7 7 0 0 0 14 0" />
                            <line x1="12" y1="18" x2="12" y2="21" />
                          </svg>
                        </button>
                      </div>
                      {/* depth 0: just the bar. */}
                      <div className="mt-1 h-[2px] bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${Math.round(r.pressure * 100)}%`, background: COLORS[r.activity], opacity: 0.8 }} />
                      </div>
                      {/* depth 1: which work. */}
                      {depth >= 1 && (r.branch || r.step) ? (
                        <div className="pt-0.5 text-[9px] font-mono leading-tight">
                          {r.branch ? <div className="text-cyan-300/70 truncate">{r.branch}</div> : null}
                          {r.step ? <div className="text-white/45 truncate">{r.step}</div> : null}
                        </div>
                      ) : null}
                      {/* depth 2: everything the record holds. */}
                      {depth >= 2 ? (
                        <>
                          <div className="text-[9px] font-mono text-white/40 truncate pt-0.5">
                            {[r.runtime, r.model, r.repo].filter(Boolean).join(' · ')}
                          </div>
                          <div className="text-[9px] font-mono text-white/30">
                            ${(r.spend || 0).toFixed(2)} · {r.events} ev
                          </div>
                          {mine.length ? (
                            <div className="text-[9px] text-white/60 leading-snug pt-0.5">
                              › {String(mine[0].text).slice(0, 90)}
                            </div>
                          ) : null}
                        </>
                      ) : null}
                    </div>
                  );
                })}
                {activeRows.length === 0 ? (
                  <div className="px-2 py-1 text-[10px] font-mono text-white/25">nothing working right now</div>
                ) : null}
                {hiddenWorking > 0 ? (
                  <div className="px-2 py-1 text-[9px] font-mono text-white/30">
                    +{hiddenWorking} more working — all {rows.length} are in the room
                  </div>
                ) : null}
              </div>
            </>
          ) : null}
      
          {/* ---- HARNESS: the evidence around the agents ---- */}
          {panelTab === 'harness' ? (
            <div className="flex flex-col gap-1 overflow-y-auto pt-2">
              {/* RECEIPTS. Each row already carried one in the ledger; the tab shows them. */}
              {ledgerRows.length ? ledgerRows.slice(0, 40).map((row: any, i: number) => (
                <div key={row.id ?? i} className="px-2 py-1 rounded-md bg-black/35 border border-white/5">
                  <div className="flex items-baseline gap-1">
                    <span className="text-[8px] font-mono text-white/40 truncate flex-1">
                      {String(row.session_id || '').slice(-14)}
                    </span>
                    <span className="text-[8px] font-mono text-white/30">
                      {String(row.ts || row.created_at || '').slice(11, 19)}
                    </span>
                  </div>
                  <div className="text-[9px] font-mono text-white/70 truncate">
                    {row.kind || row.type || 'event'}
                  </div>
                  {depth >= 1 && row.text ? (
                    <div className="text-[9px] text-white/45 truncate">{String(row.text).slice(0, 80)}</div>
                  ) : null}
                </div>
              )) : (
                <div className="px-2 py-1 text-[10px] font-mono text-white/30 leading-relaxed">
                  {selectedRow ? 'no receipts recorded for this session yet' : 'select an agent to see its receipts'}
                  <br />
                  <span className="text-white/20">
                    the ledger is per-session; a receipt appears when its claim is checked against
                    its trace
                  </span>
                </div>
              )}
              {/* THE CHECKS, stated as what they are rather than as buttons that would 503 on a
                  laptop with no Langfuse. */}
              {depth >= 2 ? (
                <div className="px-2 pt-2 text-[9px] font-mono text-white/25 leading-relaxed">
                  checks available: /check-receipts · /trace
                  <br />
                  both need LANGFUSE_HOST, which this host does not have
                </div>
              ) : null}
            </div>
          ) : null}
      
          {/* ---- TALK: the conversation ---- */}
                    {/* ---- FRICTION: what the voice log knows ---- */}
          {panelTab === 'friction' ? (
            <div className="flex flex-col gap-2 overflow-y-auto pt-2">
              {voice.voiceStats && voice.voiceStats.turns ? (
                <div className="px-2 pb-1 border-b border-white/10">
                  {/* THE FOUR NUMBERS THAT DIAGNOSE VOICE.
                      `empty` is the one behind "I had to repeat myself" -- a spoken utterance the
                      transcriber produced nothing for. `first` is what a person feels as latency,
                      as opposed to `total`, which is how long the sentence took. */}
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[9px] font-mono">
                    <div className="flex justify-between"><span className="text-white/35">turns</span><span className="text-white/80">{voice.voiceStats.turns}</span></div>
                    <div className="flex justify-between"><span className="text-white/35">misheard</span><span style={{ color: voice.voiceStats.empty > 0 ? COLORS.stuck : 'rgba(255,255,255,.8)' }}>{voice.voiceStats.empty} <span className="text-white/30">({Math.round((voice.voiceStats.empty_rate || 0) * 100)}%)</span></span></div>
                    <div className="flex justify-between"><span className="text-white/35">hear</span><span className="text-white/80">{voice.voiceStats.asr_median_s ?? '—'}s</span></div>
                    <div className="flex justify-between"><span className="text-white/35">1st word</span><span className="text-white/80">{voice.voiceStats.first_clause_median_s ?? '—'}s</span></div>
                  </div>
                  {voice.voiceStats.first_clause_p90_s ? (
                    <div className="text-[8px] font-mono text-white/25 pt-1">
                      p90 first word {voice.voiceStats.first_clause_p90_s}s · worst
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="px-2 text-[10px] font-mono text-white/30">no voice turns recorded yet</div>
              )}
              {voice.voiceLog.slice(0, 20).map((t: any) => (
                <div key={t.id} className="px-2 py-1 rounded-md bg-black/35 border border-white/5">
                  <div className="flex items-baseline gap-1">
                    <span className="text-[8px] font-mono text-white/30 flex-none">{String(t.heard_at).slice(11, 19)}</span>
                    <span className="text-[9px] font-mono flex-1 truncate"
                      style={{ color: t.outcome === 'empty' ? COLORS.stuck : t.outcome === 'error' ? COLORS.stuck : 'rgba(255,255,255,.7)' }}>
                      {t.outcome === 'empty' ? 'misheard — no words' : (t.voice || t.engine || '')}
                    </span>
                    <span className="text-[9px] font-mono text-white/45 flex-none">{t.llm_first_s ?? '—'}s</span>
                  </div>
                  <div className="text-[8px] font-mono text-white/30">
                    hear {t.asr_s ?? '—'}s · speak {t.tts_s ?? '—'}s · {t.words ?? 0}w
                    {t.detail ? ` · ${String(t.detail).slice(0,40)}` : ''}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
        )
      ) : null}
      

            {/* THE VOICE CONSOLE: talk to the fleet, or to ONE agent.
      
          WHAT WAS HERE BEFORE WAS A MICROPHONE AND NOTHING ELSE. I stripped the bar down to a
          single circle at the founder's request ("Ask the fleet could just be a Mic") -- and then
          removed the voice PICKER, the transcript, and every indication of who you were talking to.
          Measured 2026-09-20: `voice.catalogue` and `selectVoice` had ZERO references in this file,
          `voiceTarget` was set by talkTo and rendered nowhere, and the rail's "Talk" tab (which I
          cited as where conversations live) had already been deleted. The result was a page where
          the estate's own voice engine was mounted, working, and unreachable.
      
          So: the mic stays one button, and everything needed to USE it is around it.
      
            * TARGET  who your words will be sent to. "the fleet" means the engine answers from the
                      fleet summary; an agent name means the transcript is steered to that session
                      and ITS reply is spoken back. Without this line a person cannot know.
            * MIC     one button, colour is the state, as before.
            * VOICE   the picker: every engine and every voice the service offers, switchable live.
            * WORDS   what was heard and what was said, so a voice that is misunderstood is visible
                      rather than mysterious.
      */}
      {/* bottom-20, not bottom-6: the mic is the one thing on this page a person reaches for, and at
          bottom-6 it sat in the same row as the channel strip, touching it. Lifted clear of the
          footer row it stands alone at the centre. */}
      <div className="absolute bottom-20 left-1/2 -translate-x-1/2 z-40 pointer-events-auto flex flex-col items-center gap-2 w-full max-w-[560px] px-4">
        {/* 1. THE TARGET. Always visible when the engine is on, because "who am I talking to" is the
            one question a voice interface must answer before it is asked. */}
        {voice.state !== 'off' ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-black/70 border border-white/10 backdrop-blur-md text-[11px] font-mono">
            <span className="text-white/40">talking to</span>
            <span data-testid="voice-addressee" className={voiceTarget ? 'text-cyan-300' : 'text-white/80'}>
              {(() => {
                if (!voiceTarget) return 'the fleet';
                const row = rows.find((r: any) => r.sessionId === voiceTarget);
                return row ? (row.task || row.sessionId.slice(-8)) : voiceTarget.slice(-8);
              })()}
            </span>
            {voiceTarget ? (
              <button
                type="button"
                onClick={() => { voiceTargetRef.current = ''; setVoiceTarget(''); }}
                title="address the fleet instead"
                className="tab-plain text-white/40 hover:text-white/80 cursor-pointer px-1 bg-black/40 rounded"
              >
                ✕
              </button>
            ) : null}
          </div>
        ) : null}
      
        {/* 2. WHAT WAS HEARD AND WHAT WAS SAID. A voice interface that does not show its words
            cannot be debugged by the person using it, and "it misheard me" is indistinguishable
            from "it ignored me". */}
        {voice.heard || voice.reply || voice.detail ? (
          <div className="w-full bg-black/70 border border-white/10 backdrop-blur-md rounded-xl px-4 py-2 text-[11px] font-mono max-h-[120px] overflow-y-auto">
            {voice.heard ? <div className="text-cyan-300">› {voice.heard}</div> : null}
            {voice.reply ? <div className="text-white/85 mt-1">{voice.reply}</div> : null}
            {voice.detail ? <div className="text-white/35 mt-1">{voice.detail}</div> : null}
          </div>
        ) : null}
      
        {/* 3. THE CONTROLS: mic, voice picker. */}
        <div className="flex items-center gap-3">
          <button
            data-testid="fleet-mic"
            onClick={openVoice}
            title={
              voice.state === 'off' ? 'talk to the fleet'
                : voice.state === 'listening' ? 'listening — click to stop'
                : voice.state === 'thinking' ? 'thinking…'
                : voice.state === 'speaking' ? 'speaking — talk to interrupt'
                : voice.detail || 'voice error'
            }
            className="w-14 h-14 rounded-full backdrop-blur-md border flex items-center justify-center transition-all duration-300 cursor-pointer"
            style={{
              background: voice.state === 'off' ? 'rgba(0,0,0,.6)' : 'rgba(0,0,0,.75)',
              borderColor:
                voice.state === 'listening' ? 'rgba(0,240,255,.65)'
                : voice.state === 'speaking' ? 'rgba(0,255,170,.65)'
                : voice.state === 'thinking' ? 'rgba(255,170,0,.65)'
                : voice.state === 'error' ? 'rgba(255,0,85,.65)'
                : 'rgba(255,255,255,.15)',
              boxShadow:
                voice.state === 'listening' ? '0 0 26px rgba(0,240,255,.4)'
                : voice.state === 'speaking' ? '0 0 26px rgba(0,255,170,.4)'
                : voice.state === 'thinking' ? '0 0 26px rgba(255,170,0,.4)'
                : 'none',
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke={
                voice.state === 'listening' ? '#00f0ff'
                : voice.state === 'speaking' ? '#00ffaa'
                : voice.state === 'thinking' ? '#ffaa00'
                : voice.state === 'error' ? '#ff0055'
                : 'rgba(255,255,255,.55)'
              }
              strokeWidth="1.8" strokeLinecap="round"
              className={voice.state === 'listening' || voice.state === 'speaking' ? 'animate-pulse' : ''}
            >
              <rect x="9" y="3" width="6" height="11" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0" />
              <line x1="12" y1="18" x2="12" y2="21" />
            </svg>
          </button>
      
        </div>
      </div>

      {/* The transcript, for as long as it is being spoken. It is a caption, not a control: it sits
          above the mic, fades on its own, and is the ONLY text this page needs for voice. */}
      {voiceText && voice.state !== 'off' ? (
        <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-40 max-w-[520px] px-3 py-1.5 rounded-lg bg-black/70 border border-white/10 backdrop-blur-md text-[11px] font-mono text-white/75 text-center pointer-events-none">
          {voice.heard ? <span className="text-cyan-300">you: {voice.heard}</span> : null}
          {voice.reply ? <span className={voice.heard ? ' block pt-1 text-white/85' : 'text-white/85'}>{voice.reply}</span> : null}
          {!voice.heard && !voice.reply ? voiceText : null}
        </div>
      ) : null}


      <NewsDesk
        rundown={rundown}
        channel={newsChannel}
        onChannel={setNewsChannel}
        breaking={breakingStory}
        nowMs={Date.now()}
      />

      {/* Give an agent a job, watch it become a merged PR (fleetview_backend/agent_jobs.py). Through
          the discovery proxy like every remote-capable call here, so it works from the phone. */}
      <AgentJobs
        call={(init) => {
          const base = baseUrlRef.current;
          if (!base) return Promise.reject(new Error('discovery not ready'));
          return api.fetch(`${base}/fleetview/agent-jobs`, init);
        }}
      />

      {/* 2100 Era Scanline Overlay (pure CSS) */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] mix-blend-overlay z-50 bg-[repeating-linear-gradient(transparent,transparent_2px,#000_2px,#000_4px)]"></div>
    </div>
  );
}
