'use client';
import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export default function Home() {
  const mapContainer = useRef(null);
  const map = useRef(null);

  useEffect(() => {
    if (map.current) return;
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [30, 30],
      zoom: 2.5
    });
  }, []);

  return (
    <main style={{ width: '100vw', height: '100vh' }}>
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />
    </main>
  );
}
