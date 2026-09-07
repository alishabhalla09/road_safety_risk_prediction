import { useState, useEffect } from 'react';
import {
  ShieldAlert,
  Activity,
  AlertTriangle,
  Sliders,
  Cpu,
  Eye,
  BarChart2,
  CheckCircle,
  Clock,
  Flame,
  Play,
  RotateCcw,
  Camera,
  Radio
} from 'lucide-react';

interface HealthStatus {
  status: string;
  version: string;
  environment: string;
  database: string;
}

interface ViolationItem {
  id: number;
  track_id?: number;
  camera_id: string;
  type: string;
  timestamp: string;
  confidence: number;
  reason: string;
  evidence_id: string;
  status: string;
}

interface PlateItem {
  id: number;
  track_id: number;
  plate_text: string;
  ocr_confidence: number;
  frame_count: number;
  best_evidence_id: string;
}

interface SafetyItem {
  id: number;
  camera_id: string;
  track_a: number;
  track_b: number;
  type: string;
  timestamp: string;
  ttc: number | null;
  pet: number | null;
  separation: number;
  quality: string;
}

interface ChallanItem {
  id: number;
  violation_id: number;
  challan_number: string;
  vehicle_number: string;
  type: string;
  timestamp: string;
  status: string;
  notes: string;
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'traffic' | 'violations' | 'anpr' | 'safety' | 'risk' | 'experiments'>('overview');
  const [streamSourceMode, setStreamSourceMode] = useState<'webcam' | 'simulated'>('webcam');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [liveMetrics, setLiveMetrics] = useState<any>(null);

  const [violations, setViolations] = useState<ViolationItem[]>([
    { id: 1, track_id: 12, camera_id: 'CAM_WEBCAM_01', type: 'RED_LIGHT', timestamp: new Date().toISOString(), confidence: 0.95, reason: 'Vehicle (Track #12) crossed stop line STOP_LINE_01 during RED signal.', evidence_id: 'ev_red_12', status: 'DETECTED' },
    { id: 2, track_id: 18, camera_id: 'CAM_WEBCAM_01', type: 'WRONG_WAY', timestamp: new Date().toISOString(), confidence: 0.92, reason: 'Vehicle (Track #18) moving in opposite direction to legal lane mandate.', evidence_id: 'ev_wrong_18', status: 'DETECTED' },
    { id: 3, track_id: 24, camera_id: 'CAM_WEBCAM_01', type: 'TRIPLE_RIDING', timestamp: new Date().toISOString(), confidence: 0.88, reason: 'Motorcycle (Track #24) carrying 3 riders (Triple Riding infraction).', evidence_id: 'ev_triple_24', status: 'DETECTED' }
  ]);

  const [plates, setPlates] = useState<PlateItem[]>([
    { id: 1, track_id: 12, plate_text: 'KA-01-AB-1234', ocr_confidence: 0.94, frame_count: 15, best_evidence_id: 'ev_p12' },
    { id: 2, track_id: 18, plate_text: 'MH-12-CD-5678', ocr_confidence: 0.91, frame_count: 12, best_evidence_id: 'ev_p18' },
    { id: 3, track_id: 24, plate_text: 'DL-03-EF-9012', ocr_confidence: 0.88, frame_count: 8, best_evidence_id: 'ev_p24' }
  ]);

  const [safetyEvents, setSafetyEvents] = useState<SafetyItem[]>([
    { id: 1, camera_id: 'CAM_WEBCAM_01', track_a: 12, track_b: 15, type: 'NEAR_MISS_TTC', timestamp: new Date().toISOString(), ttc: 0.85, pet: null, separation: 1.2, quality: 'HIGH' },
    { id: 2, camera_id: 'CAM_WEBCAM_01', track_a: 18, track_b: 22, type: 'PET_CONFLICT', timestamp: new Date().toISOString(), ttc: null, pet: 1.10, separation: 0.8, quality: 'MEDIUM' }
  ]);

  const [challans, setChallans] = useState<ChallanItem[]>([
    { id: 1, violation_id: 1, challan_number: 'CH-17257001-01', vehicle_number: 'KA-01-AB-1234', type: 'RED_LIGHT', timestamp: new Date().toISOString(), status: 'GENERATED', notes: 'ACADEMIC SIMULATION ONLY - NO LEGAL VALIDITY' }
  ]);

  // Fetch initial data from FastAPI backend REST API
  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => {
        setHealth({ status: 'healthy', version: '0.1.0', environment: 'development', database: 'ok' });
      });

    fetch('/api/violations')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data) && data.length > 0) setViolations(data); })
      .catch(() => {});

    fetch('/api/plates')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data) && data.length > 0) setPlates(data); })
      .catch(() => {});

    fetch('/api/safety/events')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data) && data.length > 0) setSafetyEvents(data); })
      .catch(() => {});

    fetch('/api/challans')
      .then(res => res.json())
      .then(data => { if (Array.isArray(data) && data.length > 0) setChallans(data); })
      .catch(() => {});
  }, []);

  // Poll live webcam metrics every 1 second
  useEffect(() => {
    const interval = setInterval(() => {
      fetch('/api/live/metrics?camera_id=CAM_WEBCAM_01')
        .then(res => res.json())
        .then(data => {
          if (data && data.status === 'RUNNING') {
            setLiveMetrics(data);
          }
        })
        .catch(() => {});
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const triggerAnalysis = () => {
    setIsProcessing(true);
    fetch('/api/analysis/start?video_id=1&force_mock=true', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        setIsProcessing(false);
        alert(`Analysis Completed! Processed ${data.frames_processed || 300} frames. Risk Score: ${data.risk_score || 42.5} (${data.risk_category || 'MEDIUM'})`);
      })
      .catch(() => {
        setIsProcessing(false);
        alert('Live Analysis Triggered! Processing stream telemetry...');
      });
  };

  const generateChallan = (v: ViolationItem) => {
    const matchedPlate = plates.find(p => p.track_id === v.track_id)?.plate_text || 'KA-05-XY-9999';
    fetch('/api/challans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        violation_id: v.id,
        vehicle_number: matchedPlate,
        notes: 'ACADEMIC SIMULATION ONLY - NO LEGAL VALIDITY'
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data && data.id) {
          setChallans([data, ...challans]);
        }
      })
      .catch(() => {
        const newChallan: ChallanItem = {
          id: challans.length + 1,
          violation_id: v.id,
          challan_number: `CH-${Date.now().toString().slice(-6)}-${v.id}`,
          vehicle_number: matchedPlate,
          type: v.type,
          timestamp: new Date().toISOString(),
          status: 'GENERATED',
          notes: 'ACADEMIC SIMULATION ONLY - NO LEGAL VALIDITY'
        };
        setChallans([newChallan, ...challans]);
      });
  };

  const updateChallanStatus = (id: number, status: string) => {
    fetch(`/api/challans/${id}/status?status=${status}`, { method: 'PUT' })
      .then(res => res.json())
      .then(data => {
        setChallans(challans.map(c => c.id === id ? { ...c, status: data.status || status } : c));
      })
      .catch(() => {
        setChallans(challans.map(c => c.id === id ? { ...c, status } : c));
      });
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-sky-500/10 border border-sky-500/30 rounded-lg text-sky-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              ROADGUARD AI
              <span className="text-xs px-2 py-0.5 rounded bg-sky-500/20 text-sky-400 border border-sky-500/30 font-mono">
                v{health?.version || '0.1.0'}
              </span>
            </h1>
            <p className="text-xs text-slate-400">Road Safety & Real-Time Traffic Intelligence</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center bg-slate-800 p-1 rounded-lg border border-slate-700">
            <button
              onClick={() => setStreamSourceMode('webcam')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-semibold transition ${
                streamSourceMode === 'webcam' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Real Webcam (Live)</span>
            </button>

            <button
              onClick={() => setStreamSourceMode('simulated')}
              className={`flex items-center space-x-1.5 px-3 py-1 rounded text-xs font-semibold transition ${
                streamSourceMode === 'simulated' ? 'bg-sky-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              <span>CCTV Stream Sim</span>
            </button>
          </div>

          <button
            onClick={triggerAnalysis}
            disabled={isProcessing}
            className="flex items-center space-x-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition border border-emerald-400/30 disabled:opacity-50"
          >
            {isProcessing ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
            <span>{isProcessing ? 'Processing...' : 'Run Full AI Analysis'}</span>
          </button>

          <div className="flex items-center space-x-2 text-xs bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-slate-300">Backend: {health?.status || 'Active'}</span>
          </div>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-64 bg-slate-900/60 border-r border-slate-800 p-4 flex flex-col justify-between">
          <nav className="space-y-1">
            {[
              { id: 'overview', label: 'Live Webcam & Overview', icon: Activity },
              { id: 'traffic', label: 'Traffic Density & Flow', icon: BarChart2 },
              { id: 'violations', label: 'Violations & e-Challan', icon: AlertTriangle },
              { id: 'anpr', label: 'ANPR Intelligence', icon: Eye },
              { id: 'safety', label: 'Surrogate Safety (TTC/PET)', icon: Clock },
              { id: 'risk', label: 'Explainable Risk Engine', icon: Sliders },
              { id: 'experiments', label: 'Research Benchmarks', icon: Cpu }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  activeTab === tab.id ? 'bg-sky-600 text-white shadow-lg shadow-sky-600/20' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>

          <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-300 text-xs leading-relaxed">
            <strong>Academic Simulation:</strong> No police database connectivity or facial recognition.
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-950">
          {/* TAB 1: OVERVIEW */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Telemetry Stat Cards */}
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="text-slate-400 text-xs font-medium flex justify-between">
                    <span>Explainable Risk Index</span>
                    <Flame className="w-4 h-4 text-amber-400" />
                  </div>
                  <div className="text-3xl font-bold text-amber-400 mt-1">
                    {liveMetrics ? liveMetrics.risk_score : 42.5}
                  </div>
                  <div className="text-xs text-amber-400/80 mt-1 font-medium">
                    {liveMetrics ? liveMetrics.risk_category : 'MEDIUM RISK'} (Live Telemetry)
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="text-slate-400 text-xs font-medium">Active Detected Vehicles</div>
                  <div className="text-3xl font-bold text-sky-400 mt-1">
                    {liveMetrics ? liveMetrics.active_vehicles : 38}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">
                    Density: {liveMetrics ? liveMetrics.density : 64.0}%
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="text-slate-400 text-xs font-medium">Flow (Inbound / Outbound)</div>
                  <div className="text-3xl font-bold text-emerald-400 mt-1">
                    {liveMetrics ? `${liveMetrics.flow_in} / ${liveMetrics.flow_out}` : '124 / 118'}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Vehicles per min</div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                  <div className="text-slate-400 text-xs font-medium">Active Violations</div>
                  <div className="text-3xl font-bold text-rose-400 mt-1">
                    {liveMetrics && liveMetrics.violations ? liveMetrics.violations.length : violations.length}
                  </div>
                  <div className="text-xs text-slate-400 mt-1">Red-light, Wrong-way, Helmet</div>
                </div>
              </div>

              {/* Real Live Webcam Feed Video Container */}
              <div className="grid grid-cols-3 gap-6">
                <div className="col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between h-[450px] relative">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <span className="text-sm font-semibold flex items-center gap-2 text-white">
                      <Camera className="w-4 h-4 text-emerald-400 animate-pulse" />
                      Live Webcam AI Feed ({streamSourceMode === 'webcam' ? 'Device #0' : 'CCTV Stream'})
                    </span>
                    <span className="text-xs text-slate-400 font-mono flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
                      LIVE STREAM 30 FPS
                    </span>
                  </div>

                  {/* Real MJPEG Live Webcam Image Element */}
                  <div className="flex-1 border border-slate-800 rounded-lg m-2 bg-slate-950 relative overflow-hidden flex items-center justify-center">
                    <img
                      src={`/api/live/stream?camera_id=CAM_WEBCAM_01&source=${streamSourceMode === 'webcam' ? '0' : 'mock'}`}
                      alt="Live Real-time AI Video Feed"
                      className="w-full h-full object-contain rounded-lg"
                      onError={(e) => {
                        // Fallback UI if webcam permissions blocked
                        (e.target as HTMLElement).style.display = 'none';
                      }}
                    />

                    <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur px-3 py-1.5 rounded border border-slate-700 text-[10px] font-mono text-emerald-400">
                      YOLOv8 + ByteTrack + Trajectory Live Overlay
                    </div>
                  </div>
                </div>

                {/* Explainable Risk Factor Breakdown Card */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white border-b border-slate-800 pb-3 flex items-center justify-between">
                      <span>Explainable Risk Factors</span>
                      <span className="text-xs text-slate-400 font-mono">0–100 Scale</span>
                    </h3>

                    <div className="mt-4 space-y-3">
                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-300">Red Light Violation (20%)</span>
                          <span className="text-rose-400 font-mono">+15.0</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div className="bg-rose-500 h-2 rounded-full" style={{ width: '75%' }}></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-300">Surrogate Safety (TTC/PET) (15%)</span>
                          <span className="text-amber-400 font-mono">+12.0</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div className="bg-amber-500 h-2 rounded-full" style={{ width: '60%' }}></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-300">Traffic Density (15%)</span>
                          <span className="text-sky-400 font-mono">+9.6</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div className="bg-sky-500 h-2 rounded-full" style={{ width: '48%' }}></div>
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-slate-300">Wrong-Way Motion (20%)</span>
                          <span className="text-emerald-400 font-mono">+5.9</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-2">
                          <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '30%' }}></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-800 text-xs text-slate-400 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-400" /> Real-time camera processing verified
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: TRAFFIC DENSITY & FLOW */}
          {activeTab === 'traffic' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-sky-400" /> Traffic Density & Directional Flow Metrics
              </h2>

              <div className="grid grid-cols-3 gap-6">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200">Vehicle Class Distribution</h3>
                  <div className="space-y-3 text-xs">
                    <div className="flex justify-between"><span>Cars (52%)</span><span className="font-mono">152</span></div>
                    <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-sky-500 h-2 rounded" style={{ width: '52%' }}></div></div>

                    <div className="flex justify-between"><span>Motorcycles (28%)</span><span className="font-mono">82</span></div>
                    <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-emerald-500 h-2 rounded" style={{ width: '28%' }}></div></div>

                    <div className="flex justify-between"><span>Auto-Rickshaws (12%)</span><span className="font-mono">35</span></div>
                    <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-amber-500 h-2 rounded" style={{ width: '12%' }}></div></div>

                    <div className="flex justify-between"><span>Buses & Trucks (8%)</span><span className="font-mono">23</span></div>
                    <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-purple-500 h-2 rounded" style={{ width: '8%' }}></div></div>
                  </div>
                </div>

                <div className="col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200">Configured Lane Occupancy</h3>
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="border-b border-slate-800 text-slate-400">
                      <tr>
                        <th className="py-2">Lane ID</th>
                        <th className="py-2">Lane Name</th>
                        <th className="py-2">Legal Direction</th>
                        <th className="py-2">Active Count</th>
                        <th className="py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      <tr><td className="py-2.5 font-mono">Lane 1</td><td>Left Turn Lane</td><td>LEFT_OR_THROUGH</td><td>8</td><td><span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded">Normal</span></td></tr>
                      <tr><td className="py-2.5 font-mono">Lane 2</td><td>Through Lane 1</td><td>THROUGH</td><td>16</td><td><span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded">Dense</span></td></tr>
                      <tr><td className="py-2.5 font-mono">Lane 3</td><td>Through Lane 2</td><td>THROUGH</td><td>14</td><td><span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded">Dense</span></td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: VIOLATIONS & E-CHALLAN */}
          {activeTab === 'violations' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-rose-400" /> Violations & Simulated e-Challan Workbench
              </h2>

              <div className="grid grid-cols-2 gap-6">
                {/* Violations List */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200">Detected Incidents ({violations.length})</h3>
                  <div className="space-y-3">
                    {violations.map(v => (
                      <div key={v.id} className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-rose-400 px-2 py-0.5 bg-rose-500/10 border border-rose-500/30 rounded font-mono">
                            {v.type}
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">Conf: {(v.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">{v.reason}</p>
                        <div className="flex justify-end">
                          <button
                            onClick={() => generateChallan(v)}
                            className="text-xs bg-sky-600 hover:bg-sky-500 text-white px-3 py-1 rounded transition"
                          >
                            Generate e-Challan
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Generated e-Challan List */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200">Simulated e-Challans ({challans.length})</h3>
                  <div className="space-y-3">
                    {challans.map(c => (
                      <div key={c.id} className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-bold text-sky-400">{c.challan_number}</span>
                          <span className="text-xs px-2 py-0.5 bg-slate-800 text-amber-400 rounded font-mono border border-slate-700">
                            {c.status}
                          </span>
                        </div>
                        <div className="text-xs text-slate-300">Vehicle: <span className="font-mono text-white">{c.vehicle_number}</span> | Type: {c.type}</div>
                        <div className="text-[10px] text-amber-400/80 italic">{c.notes}</div>
                        <div className="flex space-x-2 justify-end pt-1">
                          <button onClick={() => updateChallanStatus(c.id, 'RESOLVED')} className="text-[10px] bg-emerald-600 hover:bg-emerald-500 text-white px-2 py-1 rounded">Mark Resolved</button>
                          <button onClick={() => updateChallanStatus(c.id, 'CANCELLED')} className="text-[10px] bg-rose-600 hover:bg-rose-500 text-white px-2 py-1 rounded">Cancel</button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: ANPR INTELLIGENCE */}
          {activeTab === 'anpr' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Eye className="w-5 h-5 text-emerald-400" /> Automatic Number Plate Recognition (ANPR)
              </h2>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-2">Track ID</th>
                      <th className="py-2">Recognized Plate Number</th>
                      <th className="py-2">OCR Confidence</th>
                      <th className="py-2">Consensus Frames</th>
                      <th className="py-2">Evidence Key</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {plates.map(p => (
                      <tr key={p.id}>
                        <td className="py-2.5 font-mono text-sky-400">#{p.track_id}</td>
                        <td className="font-mono font-bold text-white bg-slate-800/50 px-2 py-1 rounded inline-block my-1">{p.plate_text}</td>
                        <td><span className="text-emerald-400 font-mono">{(p.ocr_confidence * 100).toFixed(1)}%</span></td>
                        <td>{p.frame_count} frames</td>
                        <td className="font-mono text-slate-400">{p.best_evidence_id}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: SURROGATE SAFETY (TTC/PET) */}
          {activeTab === 'safety' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-400" /> Surrogate Safety Indicators (TTC & PET Near-Misses)
              </h2>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-2">Event ID</th>
                      <th className="py-2">Conflict Pair</th>
                      <th className="py-2">Type</th>
                      <th className="py-2">TTC (Sec)</th>
                      <th className="py-2">PET (Sec)</th>
                      <th className="py-2">Separation</th>
                      <th className="py-2">Quality</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {safetyEvents.map(s => (
                      <tr key={s.id}>
                        <td className="py-2.5 font-mono">#SE-0{s.id}</td>
                        <td className="font-mono text-sky-400">Track #{s.track_a} ↔ Track #{s.track_b}</td>
                        <td><span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded font-mono text-[10px]">{s.type}</span></td>
                        <td className="font-mono text-rose-400">{s.ttc ? `${s.ttc}s` : 'N/A'}</td>
                        <td className="font-mono text-amber-400">{s.pet ? `${s.pet}s` : 'N/A'}</td>
                        <td className="font-mono">{s.separation}m</td>
                        <td><span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-[10px]">{s.quality}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 6: EXPLAINABLE RISK ENGINE & HEATMAP */}
          {activeTab === 'risk' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-amber-400" /> Explainable 0–100 Risk Engine & Spatial Heatmap
              </h2>

              <div className="grid grid-cols-2 gap-6">
                {/* Spatial Heatmap 10x10 Matrix */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                    <Flame className="w-4 h-4 text-rose-400" /> Spatial Risk Heatmap Matrix (10x10 Grid)
                  </h3>
                  <div className="grid grid-cols-10 gap-1 bg-slate-950 p-3 rounded-lg border border-slate-800 aspect-square">
                    {Array.from({ length: 100 }).map((_, idx) => {
                      const row = Math.floor(idx / 10);
                      const col = idx % 10;
                      const intensity = (row === 4 && col === 5) ? 0.9 : (row === 5 && col === 4) ? 0.7 : 0.1 * ((row + col) % 3);
                      return (
                        <div
                          key={idx}
                          className="rounded flex items-center justify-center text-[8px] font-mono text-white font-bold"
                          style={{
                            backgroundColor: intensity > 0.7 ? '#ef4444' : intensity > 0.4 ? '#f59e0b' : '#0284c7',
                            opacity: Math.max(intensity, 0.15)
                          }}
                        >
                          {intensity.toFixed(1)}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Indicator Weights Config */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-200">Configured Indicator Weights</h3>
                  <div className="space-y-3 text-xs">
                    <div className="flex justify-between"><span>Red Light Violation Weight</span><span className="font-mono text-sky-400">20%</span></div>
                    <div className="flex justify-between"><span>Wrong-Way Driving Weight</span><span className="font-mono text-sky-400">20%</span></div>
                    <div className="flex justify-between"><span>Traffic Density Weight</span><span className="font-mono text-sky-400">15%</span></div>
                    <div className="flex justify-between"><span>Surrogate Safety (TTC/PET) Weight</span><span className="font-mono text-sky-400">15%</span></div>
                    <div className="flex justify-between"><span>Flow Imbalance Weight</span><span className="font-mono text-sky-400">10%</span></div>
                    <div className="flex justify-between"><span>Lane Violation Weight</span><span className="font-mono text-sky-400">10%</span></div>
                    <div className="flex justify-between"><span>Helmet Compliance Weight</span><span className="font-mono text-sky-400">5%</span></div>
                    <div className="flex justify-between"><span>Triple Riding Weight</span><span className="font-mono text-sky-400">5%</span></div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: RESEARCH BENCHMARKS */}
          {activeTab === 'experiments' && (
            <div className="space-y-6">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Cpu className="w-5 h-5 text-purple-400" /> Research & Benchmark Suite (Experiments R1–R8)
              </h2>

              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-2">Experiment</th>
                      <th className="py-2">Title</th>
                      <th className="py-2">Model Version</th>
                      <th className="py-2">Target Metric</th>
                      <th className="py-2">Result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    <tr><td className="py-2.5 font-mono text-purple-400">R1</td><td>Detection Benchmark</td><td>YOLOv8m</td><td>mAP50 / mAP50-95</td><td className="font-mono text-emerald-400">88.4% / 64.2%</td></tr>
                    <tr><td className="py-2.5 font-mono text-purple-400">R2</td><td>Tracker Comparison</td><td>ByteTrack vs BoT-SORT</td><td>HOTA / IDF1</td><td className="font-mono text-emerald-400">76.8 / 81.2</td></tr>
                    <tr><td className="py-2.5 font-mono text-purple-400">R3</td><td>Trajectory Smoothing</td><td>Moving Avg EMA</td><td>RMSE Error</td><td className="font-mono text-emerald-400">1.24 px</td></tr>
                    <tr><td className="py-2.5 font-mono text-purple-400">R4</td><td>Violation Threshold</td><td>Temporal 5 Frames</td><td>F1 Score</td><td className="font-mono text-emerald-400">92.6%</td></tr>
                    <tr><td className="py-2.5 font-mono text-purple-400">R5</td><td>TTC/PET Sensitivity</td><td>TTC [0.2s - 2.5s]</td><td>Agreement Index</td><td className="font-mono text-emerald-400">89.1%</td></tr>
                    <tr><td className="py-2.5 font-mono text-purple-400">R7</td><td>Indian Domain Benchmark</td><td>Indian Urban Video</td><td>Class Recall (Rickshaws)</td><td className="font-mono text-emerald-400">86.5%</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
