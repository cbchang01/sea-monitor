'use client';
import { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { createClient } from '@supabase/supabase-js';

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_KEY
);

export default function Home() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const [stats, setStats] = useState({ total: 0, sanctioned: 0 });

  useEffect(() => {
    if (map.current) return;
    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [30, 30],
      zoom: 2.5
    });
    map.current.on('load', () => {
      loadVessels();
    });
  }, []);

  async function loadVessels() {
    const { data: vessels, error: ve } = await supabase
      .from('vessels')
      .select('*')
      .order('id', { ascending: false })
      .limit(2000);

    const { data: sanctions, error: se } = await supabase
      .from('sanctions')
      .select('mmsi, imo, name')
      .limit(2000);

    console.log('Vessels:', vessels?.length, 'Error:', ve);
    console.log('Sanctions:', sanctions?.length, 'Error:', se);

    if (!vessels || vessels.length === 0) return;

    const sanctionedMmsi = new Set(
      (sanctions || []).filter(s => s.mmsi).map(s => s.mmsi.replace(/\s/g, ''))
    );
    const sanctionedImo = new Set(
      (sanctions || []).filter(s => s.imo).map(s => s.imo.replace(/\s/g, ''))
    );

    const geojson = {
      type: 'FeatureCollection',
      features: vessels.map(v => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [v.lng, v.lat] },
        properties: {
          mmsi: v.mmsi,
          name: v.name || 'Unknown',
          speed: v.speed,
          imo: v.imo || '',
          sanctioned: sanctionedMmsi.has(v.mmsi) || (v.imo && sanctionedImo.has(v.imo))
        }
      }))
    };

    const sanctionedCount = geojson.features.filter(f => f.properties.sanctioned).length;
    console.log('Sample vessel IMOs:', vessels.slice(0,5).map(v => v.imo));
    console.log('Sample sanction IMOs:', [...sanctionedImo].slice(0,5));
    console.log('Test vessel:', vessels.find(v => v.mmsi === '123456789'));
    setStats({ total: vessels.length, sanctioned: sanctionedCount });

    if (map.current.getSource('vessels')) {
      map.current.getSource('vessels').setData(geojson);
      return;
    }

    map.current.addSource('vessels', { type: 'geojson', data: geojson });

    map.current.addLayer({
      id: 'vessels-clean',
      type: 'circle',
      source: 'vessels',
      filter: ['==', ['get', 'sanctioned'], false],
      paint: {
        'circle-radius': 3,
        'circle-color': '#3b9eff',
        'circle-opacity': 0.7
      }
    });

    map.current.addLayer({
      id: 'vessels-sanctioned',
      type: 'circle',
      source: 'vessels',
      filter: ['==', ['get', 'sanctioned'], true],
      paint: {
        'circle-radius': 7,
        'circle-color': '#ff4444',
        'circle-opacity': 0.9
      }
    });

    map.current.on('click', 'vessels-sanctioned', (e) => {
      const props = e.features[0].properties;
      new mapboxgl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-family:sans-serif;padding:4px">
            <div style="color:#ff4444;font-weight:bold;margin-bottom:4px">SANCTIONED</div>
            <div style="font-weight:bold">${props.name}</div>
            <div style="color:#888;font-size:12px">MMSI: ${props.mmsi}</div>
            <div style="color:#888;font-size:12px">IMO: ${props.imo}</div>
            <div style="color:#888;font-size:12px">Speed: ${props.speed} kts</div>
          </div>
        `)
        .addTo(map.current);
    });

    map.current.on('click', 'vessels-clean', (e) => {
      const props = e.features[0].properties;
      new mapboxgl.Popup()
        .setLngLat(e.lngLat)
        .setHTML(`
          <div style="font-family:sans-serif;padding:4px">
            <div style="font-weight:bold">${props.name}</div>
            <div style="color:#888;font-size:12px">MMSI: ${props.mmsi}</div>
            <div style="color:#888;font-size:12px">IMO: ${props.imo}</div>
            <div style="color:#888;font-size:12px">Speed: ${props.speed} kts</div>
          </div>
        `)
        .addTo(map.current);
    });

    map.current.on('mouseenter', 'vessels-sanctioned', () => {
      map.current.getCanvas().style.cursor = 'pointer';
    });
    map.current.on('mouseleave', 'vessels-sanctioned', () => {
      map.current.getCanvas().style.cursor = '';
    });
    map.current.on('mouseenter', 'vessels-clean', () => {
      map.current.getCanvas().style.cursor = 'pointer';
    });
    map.current.on('mouseleave', 'vessels-clean', () => {
      map.current.getCanvas().style.cursor = '';
    });
  }

  return (
    <main style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <div ref={mapContainer} style={{ width: '100%', height: '100%' }} />
      <div style={{
        position: 'absolute', top: 16, left: 16,
        background: 'rgba(13,30,58,0.9)',
        border: '0.5px solid rgba(255,255,255,0.15)',
        borderRadius: 8, padding: '12px 16px',
        color: 'white', fontFamily: 'sans-serif'
      }}>
        <div style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>🌊 Sea Monitor</div>
        <div style={{ fontSize: 12, color: '#7dc3ff' }}>Vessels tracked: {stats.total.toLocaleString()}</div>
        <div style={{ fontSize: 12, color: '#ff4444' }}>Sanctioned: {stats.sanctioned}</div>
      </div>
    </main>
  );
}
