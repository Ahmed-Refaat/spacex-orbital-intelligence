import { useMemo } from 'react'
import * as THREE from 'three'
import { EARTH_RADIUS } from '@/constants/scene'

const atmosphereVertexShader = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vPosition = position;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const atmosphereFragmentShader = `
  varying vec3 vNormal;
  varying vec3 vPosition;
  
  uniform vec3 glowColor;
  uniform float intensity;
  uniform float falloff;
  
  void main() {
    // Calculate glow based on viewing angle
    vec3 viewVector = normalize(cameraPosition - vPosition);
    float glowIntensity = pow(falloff - dot(vNormal, viewVector), intensity);
    
    // Apply color with calculated intensity
    vec3 color = glowColor * glowIntensity;
    float alpha = glowIntensity;
    
    gl_FragColor = vec4(color, alpha);
  }
`

interface AtmosphereGlowProps {
  enabled?: boolean
  color?: THREE.Color
  intensity?: number
  falloff?: number
}

export function AtmosphereGlow({
  enabled = true,
  color = new THREE.Color(0x4a90e2),
  intensity = 2.0,
  falloff = 0.7
}: AtmosphereGlowProps) {
  
  const shaderMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: atmosphereVertexShader,
      fragmentShader: atmosphereFragmentShader,
      uniforms: {
        glowColor: { value: color },
        intensity: { value: intensity },
        falloff: { value: falloff }
      },
      side: THREE.BackSide,
      blending: THREE.AdditiveBlending,
      transparent: true,
      depthWrite: false
    })
  }, [color, intensity, falloff])

  if (!enabled) return null

  return (
    <mesh>
      <sphereGeometry args={[EARTH_RADIUS * 1.15, 64, 64]} />
      <primitive object={shaderMaterial} attach="material" />
    </mesh>
  )
}

// Aurora-like atmospheric effects
export function AuroraEffect({ enabled = false }: { enabled?: boolean }) {
  const auroraMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        
        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        uniform float time;
        
        // Noise function for organic aurora movement
        float noise(vec2 p) {
          return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
        }
        
        void main() {
          // Aurora mainly near poles
          float latitude = vUv.y;
          float polarFactor = smoothstep(0.6, 1.0, latitude) + smoothstep(0.4, 0.0, latitude);
          
          if (polarFactor < 0.1) {
            discard;
          }
          
          // Animated waves
          float wave1 = sin(vUv.x * 10.0 + time * 0.5) * 0.5 + 0.5;
          float wave2 = sin(vUv.x * 15.0 - time * 0.3) * 0.5 + 0.5;
          float combined = (wave1 + wave2) * 0.5;
          
          // Aurora colors (green/blue/purple)
          vec3 color1 = vec3(0.1, 0.8, 0.3); // Green
          vec3 color2 = vec3(0.3, 0.5, 1.0); // Blue
          vec3 color3 = vec3(0.8, 0.2, 0.8); // Purple
          
          vec3 color = mix(color1, color2, combined);
          color = mix(color, color3, wave2);
          
          float alpha = combined * polarFactor * 0.6;
          
          gl_FragColor = vec4(color, alpha);
        }
      `,
      uniforms: {
        time: { value: 0 }
      },
      side: THREE.DoubleSide,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  }, [])

  if (!enabled) return null

  return (
    <mesh>
      <sphereGeometry args={[EARTH_RADIUS * 1.08, 64, 64]} />
      <primitive object={auroraMaterial} attach="material" />
    </mesh>
  )
}

// City lights effect for night side
export function CityLights({ enabled = false }: { enabled?: boolean }) {
  const cityLightsMaterial = useMemo(() => {
    return new THREE.ShaderMaterial({
      vertexShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vPosition;
        
        void main() {
          vUv = uv;
          vNormal = normalize(normalMatrix * normal);
          vPosition = (modelMatrix * vec4(position, 1.0)).xyz;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec2 vUv;
        varying vec3 vNormal;
        varying vec3 vPosition;
        
        uniform vec3 sunDirection;
        
        // Simple noise for city distribution
        float random(vec2 st) {
          return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453123);
        }
        
        void main() {
          // Calculate day/night (dot product with sun direction)
          float sunDot = dot(vNormal, sunDirection);
          
          // Only show on night side
          if (sunDot > -0.2) {
            discard;
          }
          
          // Create city light pattern
          vec2 gridUv = vUv * 200.0; // Create grid
          float cityPattern = step(0.95, random(floor(gridUv)));
          
          // More cities around certain latitudes (populated areas)
          float latitudeFactor = smoothstep(0.3, 0.7, vUv.y) * smoothstep(0.7, 0.3, vUv.y);
          cityPattern *= latitudeFactor;
          
          // Golden city light color
          vec3 lightColor = vec3(1.0, 0.9, 0.6);
          
          // Fade based on night intensity
          float nightIntensity = smoothstep(-0.2, -0.5, sunDot);
          
          float alpha = cityPattern * nightIntensity * 0.8;
          
          gl_FragColor = vec4(lightColor, alpha);
        }
      `,
      uniforms: {
        sunDirection: { value: new THREE.Vector3(1, 0, 0) }
      },
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
  }, [])

  if (!enabled) return null

  return (
    <mesh>
      <sphereGeometry args={[EARTH_RADIUS * 1.001, 128, 128]} />
      <primitive object={cityLightsMaterial} attach="material" />
    </mesh>
  )
}
