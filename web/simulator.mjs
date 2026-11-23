// Actual MuJoCo WebAssembly drives the model. Rendering only reads engine state.
const START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR";
const SYMBOLS = {p:"♟",n:"♞",b:"♝",r:"♜",q:"♛",k:"♚",P:"♙",N:"♘",B:"♗",R:"♖",Q:"♕",K:"♔"};
const STEPS = 600;
const TOLERANCE = .002;

export function center(square) {
  return [.13 + (Number(square[1]) - 1) * .03, (square.charCodeAt(0) - 100.5) * .03];
}

export function inverse([x, y]) {
  const a = .24, b = .20;
  const cos = (x*x + y*y - a*a - b*b) / (2*a*b);
  if (Math.abs(cos) > 1) throw Error("Target is outside the workspace");
  const elbow = Math.acos(cos);
  return [Math.atan2(y,x) - Math.atan2(b*Math.sin(elbow),a+b*cos), elbow];
}

export class ChessSimulation {
  constructor(engine, xml, records) {
    this.engine = engine;
    this.model = engine.MjModel.from_xml_string(xml);
    this.data = new engine.MjData(this.model);
    this.records = records;
    this.reset();
  }
  reset() {
    this.engine.mj_resetData(this.model, this.data);
    this.engine.mj_forward(this.model, this.data);
    this.index = 0;
    this.fen = START;
    this.transfer = null;
    this.manual = false;
    this.status = "Ready";
  }
  beginMove() {
    if (this.transfer || this.index === this.records.length || this.manual) return false;
    this.record = this.records[this.index];
    this.transferIndex = 0;
    this.beginTransfer();
    return true;
  }
  beginTransfer() {
    this.transfer = this.record.transfers[this.transferIndex];
    this.phaseTicks = 0;
    this.phase = "Approach";
    this.engine.mj_resetData(this.model, this.data);
    this.data.mocap_pos.set([...this.transfer.pick,0]);
    this.data.ctrl.set(inverse(this.transfer.pick));
    this.engine.mj_forward(this.model, this.data);
    this.status = this.record.move + " · " + this.phase;
  }
  targetJoints(values) {
    if (this.transfer) return;
    this.manual = true;
    this.data.ctrl.set(values);
    this.status = "Manual joint control";
  }
  advance() {
    if (!this.transfer && !this.manual) return;
    this.engine.mj_step(this.model, this.data);
    if (this.manual) return;
    const tcp = this.data.site_xpos;
    if (this.phase === "Transfer") this.data.mocap_pos.set(tcp.subarray(0,3));
    if (++this.phaseTicks < STEPS) return;
    const target = this.phase === "Approach" ? this.transfer.pick : this.transfer.drop;
    if (Math.hypot(tcp[0]-target[0],tcp[1]-target[1]) > TOLERANCE) {
      this.transfer = null;
      this.status = "Motion stopped: position tolerance exceeded";
      return;
    }
    if (this.phase === "Approach") {
      this.phase = "Transfer";
      this.phaseTicks = 0;
      this.data.ctrl.set(inverse(this.transfer.drop));
      this.status = this.record.move + " · " + this.phase;
    } else if (++this.transferIndex < this.record.transfers.length) {
      this.beginTransfer();
    } else {
      this.transfer = null;
      this.fen = this.record.fen;
      this.index++;
      this.status = this.record.move + " · target reached";
    }
  }
}

function draw(canvas, sim, top) {
  const c = canvas.getContext("2d");
  const project = ([x,y,z=0]) => top ? [310+y*1080,410-x*820] : [285+1050*y+360*x,416-720*x+260*y-650*z];
  const polygon = (pts, fill, border) => {
    c.beginPath();
    pts.forEach((p,i)=>{const xy=project(p); if(i)c.lineTo(...xy); else c.moveTo(...xy);});
    c.closePath();c.fillStyle=fill;c.fill();
    if(border){c.strokeStyle=border;c.lineWidth=1;c.stroke();}
  };
  const point = (p, r, color) => {
    c.beginPath();c.arc(...project(p),r,0,2*Math.PI);c.fillStyle=color;c.fill();
  };
  c.clearRect(0,0,canvas.width,canvas.height);
  polygon([[.07,-.145],[.39,-.145],[.39,.145],[.07,.145]],"#a9b9c6","#47718b");
  const pieces = sim.fen.split(" ")[0].replaceAll("/","").replace(/[1-8]/g,n=>".".repeat(Number(n)));
  const moving = sim.transfer;
  const relocate = moving && sim.phase === "Transfer";
  const piece = (s,p) => {
    const [cx,cy]=project(p);c.font="bold 25px 'Segoe UI Symbol',sans-serif";c.textAlign="center";c.textBaseline="middle";
    c.lineWidth=2;c.strokeStyle=s===s.toUpperCase()?"#152f45":"#f3e8e0";
    c.fillStyle=s===s.toUpperCase()?"#fffaf5":"#152f45";c.strokeText(SYMBOLS[s],cx,cy);c.fillText(SYMBOLS[s],cx,cy);
  };
  for(let i=0;i<64;i++){
    const sq="abcdefgh"[i%8]+(8-Math.floor(i/8));
    const [x,y]=center(sq), a=.015;
    polygon([[x-a,y-a],[x+a,y-a],[x+a,y+a],[x-a,y+a]],(i+Math.floor(i/8))%2 ? "#7397ad":"#e8edf0");
  }
  for(let i=0;i<64;i++){
    const sq="abcdefgh"[i%8]+(8-Math.floor(i/8));
    const captured = moving && sim.transferIndex>0 && sim.record.capture && sim.record.transfers[0].square===sq;
    if (pieces[i]==="." || captured) continue;
    if (relocate && sq===moving.square) piece(pieces[i],[...sim.data.mocap_pos.subarray(0,2),.025]);
    else piece(pieces[i],[...center(sq),.015]);
  }
  const elbow = sim.data.xpos.subarray(6,8);
  const tcp = sim.data.site_xpos.subarray(0,2);
  const path = [[0,0,.075],[...elbow,.075],[...tcp,.075]];
  point([0,0,.04],23,"#20394d");
  for(const [color,width] of [["#354c5e",21],["#b8d0dc",13]]){
    c.beginPath();path.forEach((p,i)=>{if(i)c.lineTo(...project(p));else c.moveTo(...project(p));});
    c.lineCap="round";c.lineWidth=width;c.strokeStyle=color;c.stroke();
  }
  path.forEach(p=>point(p,9,"#3b687f"));
  point([...tcp,.03],5,"#e1a960");
}

export async function mount(root) {
  const status = root.querySelector("[role=status]");
  try {
    const get = async (path, type) => {
      const response = await fetch(new URL(path, import.meta.url));
      if (!response.ok) throw Error("Missing " + path);
      return response[type]();
    };
    const {default:init} = await import("https://cdn.jsdelivr.net/npm/@mujoco/mujoco@4.0.1/mujoco.js");
    const [engine,xml,moves] = await Promise.all([init(),get("chess-arm.xml","text"),get("chess-plan.json","json")]);
    const sim = new ChessSimulation(engine,xml,moves);
    const canvas = root.querySelector("canvas");
    const play = root.querySelector("#run");
    const next = root.querySelector("#step");
    const reset = root.querySelector("#reset");
    const manual = root.querySelector("#manual");
    const joints = [...root.querySelectorAll("input[type=range]")];
    const controls = root.querySelector("#joints");
    let running = false, automated = false;
    function resetMode() {
      sim.reset(); running=false; automated=false; manual.checked=false;
      controls.hidden=true;joints.forEach(j=>j.value=0);
    }
    play.onclick = () => {
      if(sim.manual || sim.index===moves.length) resetMode();
      running=!running;
      automated=true;
    };
    next.onclick = () => {
      if(sim.manual || sim.index===moves.length) resetMode();
      automated=false;
      if(!sim.transfer) sim.beginMove();
      running=true;
    };
    reset.onclick = resetMode;
    manual.onchange = () => {
      const selected=manual.checked;
      resetMode();
      if(selected){manual.checked=true;controls.hidden=false;sim.targetJoints([0,0]);running=true;}
    };
    const applyJoints = () => sim.targetJoints(joints.map(j=>Number(j.value)));
    joints.forEach(j=>j.addEventListener("input",applyJoints));
    root.querySelector("#sim-controls").disabled = false;
    function animate() {
      if (running) {
        if (automated && !sim.transfer) sim.beginMove();
        for(let i=0;i<14;i++) sim.advance();
        if (!sim.manual && !sim.transfer && (!automated || sim.index===moves.length || sim.status.startsWith("Motion stopped"))) running=false;
      }
      draw(canvas,sim,root.querySelector("#top-view").checked);
      const display = sim.index + "/" + moves.length + " · " + sim.status;
      if(status.textContent!==display)status.textContent=display;
      play.textContent=running && automated ? "Pause" : "Run sequence";
      next.disabled=Boolean(sim.transfer && running);
      requestAnimationFrame(animate);
    }
    animate();
  } catch (error) {
    status.textContent = "The simulator could not load. The recorded replay is available in the portfolio.";
    console.error(error);
  }
}

