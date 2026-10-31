"use client";

import React, {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

export interface PictureRailItem {
  id: string;
  title: string;
  artist?: string;
  year?: string;
  image: string;
  aspect?: number;
  frame?: "black" | "oak" | "white";
  mat?: boolean;
  drop?: number;
  tag?: string;
  details?: string[];
}

export interface PictureRailGalleryProps
  extends React.HTMLAttributes<HTMLElement> {
  items: PictureRailItem[];
  eyebrow?: string;
  heading?: string;
  caption?: string;
  action?: React.ReactNode;
  autoplay?: boolean;
  interval?: number;
  active?: number | null;
  onActiveChange?: (index: number | null) => void;
  onOpenChange?: (index: number | null) => void;
  labels?: {
    front?: string;
    back?: string;
    close?: string;
    open?: string;
  };
}

const DEFAULT_LABELS = {
  front: "Front",
  back: "Back",
  close: "Close",
  open: "Lift to view",
};

const PERSPECTIVE = 1200;
const GAP_FACTOR = 0.3;
const EXTRA_ACTIVE_GAP = 0.1;
const CONTACT_EPSILON = 0.05;
const RAIL_PAD = 36;
const MIN_DESKTOP_UNIT = 90;
const MAX_UNIT = 150;
const MAX_CAROUSEL_UNIT = 128;
const LIFT_SCALE = 0.06;
const SUPERSAMPLE = 2;
const ACTIVE_EXPAND = 1.12;
const LIFT_Z = 26;
const TILT_X = -6;
const AIM_MAX_DEG = 4;
const SWING_MAX_DEG = 14;
const PENDULUM_DAMPING = 2.2;
const GRAVITY_CONST = 3900;
const DRAG_SWING_GAIN = 0.08;
const FREE_SWING_GAIN = 0.16;
const IMPULSE_FORCE = 12;
const DEG_TO_RAD = 180 / Math.PI;

const FRAME_COLORS: Record<string, string> = {
  black: "color-mix(in oklab, black 82%, white)",
  oak: "color-mix(in oklab, burlywood 62%, peru)",
  white: "color-mix(in oklab, white 96%, wheat)",
};

const FRAME_LIGHTING: Record<string, number[]> = {
  black: [-0.45, 0.22, 0.06, -0.14, -0.5, 1],
  oak: [-0.36, 0.18, 0.05, -0.12, -0.42, 1],
  white: [-0.15, 0.05, 0.02, -0.05, -0.2, 0.55],
};

const BRASS_GRADIENT_HOOK =
  "linear-gradient(to bottom, color-mix(in oklab, gold 35%, white) 0%, color-mix(in oklab, goldenrod 80%, white) 32%, color-mix(in oklab, darkgoldenrod 85%, black) 72%, color-mix(in oklab, darkgoldenrod 55%, black) 100%)";
const BRASS_GRADIENT_FIXTURE =
  "linear-gradient(to bottom, color-mix(in oklab, goldenrod 50%, white) 0%, color-mix(in oklab, darkgoldenrod 78%, black) 38%, color-mix(in oklab, darkgoldenrod 48%, black) 100%)";
const BRASS_GRADIENT_STEM =
  "linear-gradient(to right, color-mix(in oklab, goldenrod 70%, white), color-mix(in oklab, darkgoldenrod 80%, black) 70%, color-mix(in oklab, darkgoldenrod 50%, black))";
const GOLD_LIGHT = "color-mix(in oklab, white 55%, gold)";
const MAT_COLOR = "color-mix(in oklab, white 95%, wheat)";
const LABEL_TEXT = "color-mix(in oklab, black 84%, white)";

function stamp(e: React.PointerEvent | PointerEvent | Event): number {
  const now = performance.now();
  return e.timeStamp > 0 && e.timeStamp <= now + 1 ? e.timeStamp : now;
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function mix(color: string, amount: number): string {
  if (amount === 0) return color;
  const pct = Math.round((1 - Math.min(1, Math.abs(amount))) * 1000) / 10;
  return `color-mix(in oklab, ${color} ${pct}%, ${amount > 0 ? "white" : "black"})`;
}

function tone(amount: number): string {
  const c = `color-mix(in oklab, ${amount > 0 ? "white" : "black"} ${Math.round(
    Math.abs(amount) * 100
  )}%, transparent)`;
  return `linear-gradient(${c}, ${c})`;
}

function restTilt(index: number): number {
  return (((index * 37 + 11) % 7) - 3) * 0.5;
}

interface FrameShape {
  frame: "black" | "oak" | "white";
  mold: number;
  mat: number;
  matB: number;
  w: number;
  h: number;
}

function shapeOf(item: PictureRailItem): FrameShape {
  const aspect = clamp(item.aspect ?? 0.8, 0.4, 2.5);
  const frame = item.frame ?? "black";
  const mold = frame === "oak" ? 0.068 : frame === "white" ? 0.058 : 0.046;
  const mat = item.mat ? 0.11 : 0;
  const matB = item.mat ? 0.022 : 0;
  const rootAspect = Math.sqrt(aspect);
  return {
    frame,
    mold,
    mat,
    matB,
    w: rootAspect + 2 * (mold + mat),
    h: 1 / rootAspect + 2 * (mold + mat) + matB,
  };
}

interface RailLayout {
  width: number;
  unit: number;
  carousel: boolean;
  railTop: number;
  railT: number;
  pivotY: number;
  tops: number[];
  stageH: number;
}

function layoutFor(
  shapes: FrameShape[],
  drops: number[],
  width: number
): RailLayout {
  const count = shapes.length;
  const totalW = shapes.reduce((sum, s) => sum + s.w, 0);
  const maxW = shapes.reduce((max, s) => Math.max(max, s.w), 0);
  const calculatedUnit = count
    ? (width - 2 * RAIL_PAD) /
      (totalW +
        Math.max(0, count - 1) * GAP_FACTOR +
        2 * EXTRA_ACTIVE_GAP +
        maxW * (ACTIVE_EXPAND - 1))
    : MAX_UNIT;
  const carousel = calculatedUnit < MIN_DESKTOP_UNIT;
  const unit = carousel
    ? clamp(width * 0.2, 92, MAX_CAROUSEL_UNIT)
    : Math.min(MAX_UNIT, calculatedUnit);

  const railTop = 6;
  const railT = Math.round(clamp(unit * 0.11, 9, 16));
  const pivotY = railTop + railT + Math.round(unit * 0.045) + 2;

  const maxH = shapes.reduce((max, s) => Math.max(max, s.h), 0) * unit;
  const midY = pivotY + unit * 0.22 + maxH / 2;

  const tops = shapes.map((s, i) =>
    Math.round(
      Math.max(
        pivotY + unit * 0.08,
        midY - (s.h * unit) / 2 + clamp(drops[i] ?? 0, -0.15, 0.6) * unit
      )
    )
  );

  const maxBottom = shapes.reduce(
    (max, s, i) => Math.max(max, (tops[i] ?? 0) + s.h * unit),
    pivotY
  );

  return {
    width,
    unit,
    carousel,
    railTop,
    railT,
    pivotY,
    tops,
    stageH: Math.round(maxBottom + 34),
  };
}

interface Sim {
  x: number[];
  vx: number[];
  tx: number[];
  sw: number[];
  vsw: number[];
  e: number[];
  ve: number[];
  te: number[];
  ty: number[];
  vty: number[];
  tty: number[];
  drag: number;
  grab: number;
  free: number;
  last: number;
  raf: number;
  hx: number[];
  hv: number[];
}

function emptySim(): Sim {
  return {
    x: [],
    vx: [],
    tx: [],
    sw: [],
    vsw: [],
    e: [],
    ve: [],
    te: [],
    ty: [],
    vty: [],
    tty: [],
    drag: -1,
    grab: 0,
    free: 0,
    last: 0,
    raf: 0,
    hx: [],
    hv: [],
  };
}

function pendulum(layout: RailLayout, shape: FrameShape, index: number): number {
  return Math.max(
    30,
    (layout.tops[index] ?? 0) - layout.pivotY + (shape.h * layout.unit) / 2
  );
}

function reach(
  sim: Sim,
  layout: RailLayout,
  shape: FrameShape,
  index: number
): [number, number] {
  const expand = clamp(sim.e[index] ?? 0, 0, 1);
  const halfW = (shape.w * layout.unit * (1 + (ACTIVE_EXPAND - 1) * expand)) / 2;
  const topDist = (layout.tops[index] ?? 0) - layout.pivotY;
  const botDist = topDist + shape.h * layout.unit;
  const rad = (sim.sw[index] ?? 0) / DEG_TO_RAD;
  const cos = Math.cos(rad);
  const sin = Math.sin(rad);
  return [
    Math.min(-halfW * cos - topDist * sin, -halfW * cos - botDist * sin),
    Math.max(halfW * cos - topDist * sin, halfW * cos - botDist * sin),
  ];
}

function resolveContacts(
  sim: Sim,
  layout: RailLayout,
  shapes: FrameShape[],
  pad: number
): void {
  const count = shapes.length;
  for (let pass = 0; pass < 3; pass++) {
    for (let i = 0; i < count - 1; i++) {
      const a = shapes[i];
      const b = shapes[i + 1];
      if (!a || !b) continue;

      const rightReachA = (sim.x[i] ?? 0) + reach(sim, layout, a, i)[1];
      const leftReachB = (sim.x[i + 1] ?? 0) + reach(sim, layout, b, i + 1)[0];
      const overlap = rightReachA - leftReachB + pad;

      if (overlap <= 0) continue;

      if (i === sim.drag) {
        sim.x[i + 1] = (sim.x[i + 1] ?? 0) + overlap;
      } else if (i + 1 === sim.drag) {
        sim.x[i] = (sim.x[i] ?? 0) - overlap;
      } else {
        sim.x[i] = (sim.x[i] ?? 0) - overlap / 2;
        sim.x[i + 1] = (sim.x[i + 1] ?? 0) + overlap / 2;
      }

      const vxA = sim.vx[i] ?? 0;
      const vxB = sim.vx[i + 1] ?? 0;
      if (vxA > vxB) {
        const avg = (vxA + vxB) / 2;
        if (i !== sim.drag) sim.vx[i] = avg;
        if (i + 1 !== sim.drag) sim.vx[i + 1] = avg;
      }
    }
  }

  if (!layout.carousel && count > 0) {
    const railRight = layout.width - 6;
    const first = shapes[0];
    const last = shapes[count - 1];

    if (first) {
      const left = reach(sim, layout, first, 0)[0];
      if ((sim.x[0] ?? 0) + left < 6) {
        sim.x[0] = 6 - left;
        sim.vx[0] = Math.abs(sim.vx[0] ?? 0) * 0.3;
      }
    }

    for (let i = 0; i < count - 1; i++) {
      const a = shapes[i];
      const b = shapes[i + 1];
      if (!a || !b) continue;
      const minX =
        (sim.x[i] ?? 0) +
        reach(sim, layout, a, i)[1] -
        reach(sim, layout, b, i + 1)[0] +
        pad;
      if ((sim.x[i + 1] ?? 0) < minX) sim.x[i + 1] = minX;
    }

    if (last) {
      const right = reach(sim, layout, last, count - 1)[1];
      if ((sim.x[count - 1] ?? 0) + right > railRight) {
        sim.x[count - 1] = railRight - right;
        sim.vx[count - 1] = -Math.abs(sim.vx[count - 1] ?? 0) * 0.3;
      }
    }

    for (let i = count - 2; i >= 0; i--) {
      const a = shapes[i];
      const b = shapes[i + 1];
      if (!a || !b) continue;
      const maxX =
        (sim.x[i + 1] ?? 0) +
        reach(sim, layout, b, i + 1)[0] -
        reach(sim, layout, a, i)[1] -
        pad;
      if ((sim.x[i] ?? 0) > maxX) sim.x[i] = maxX;
    }
  }
}

export default function PictureRailGallery({
  items,
  eyebrow,
  heading,
  caption,
  action,
  autoplay = false,
  interval = 2600,
  active: controlledActive,
  onActiveChange,
  onOpenChange,
  labels = DEFAULT_LABELS,
  className,
  ...props
}: PictureRailGalleryProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const count = items.length;
  const isControlled = controlledActive !== undefined;

  const stageRef = useRef<HTMLDivElement>(null);
  const hangRefs = useRef<(HTMLDivElement | null)[]>([]);
  const shadowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const swingRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const tiltRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const lightRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const glareRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const dimRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const shadowInnerRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const washRefs = useRef<(HTMLSpanElement | null)[]>([]);

  const simRef = useRef<Sim>(emptySim());
  const shapes = useMemo(() => items.map(shapeOf), [items]);
  const drops = useMemo(() => items.map((it) => it.drop ?? 0), [items]);

  const [containerWidth, setContainerWidth] = useState(0);
  const layout = useMemo(
    () => layoutFor(shapes, drops, containerWidth),
    [shapes, drops, containerWidth]
  );

  const [uncontrolledActive, setUncontrolledActive] = useState<number | null>(null);
  const lastActiveRef = useRef<number | null | undefined>(undefined);
  const rawActive = isControlled ? controlledActive ?? null : uncontrolledActive;
  const activeIndex =
    rawActive !== null && rawActive >= 0 && rawActive < count ? rawActive : null;

  const [focusIndex, setFocusIndex] = useState(0);
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [isPlaying, setIsPlaying] = useState(autoplay);
  const [liftHiddenIndex, setLiftHiddenIndex] = useState<number | null>(null);
  const triggerFocusIndex = useRef<number | null>(null);
  const tapTargetIndex = useRef<number>(-1);

  const pointerState = useRef({
    id: -1,
    index: -1,
    x: 0,
    y: 0,
    moved: false,
    kind: "",
    swipe: 0,
    lastX: 0,
    lastT: 0,
    v: 0,
  });

  const stateRef = useRef({
    active: null as number | null,
    layout,
    shapes,
    reduced: reducedMotion,
    count,
    openIndex: null as number | null,
    carouselIndex: Math.min(1, Math.max(0, count - 1)),
  });

  stateRef.current = {
    ...stateRef.current,
    active: activeIndex,
    layout,
    shapes,
    reduced: reducedMotion,
    count,
    openIndex,
  };

  const callbacksRef = useRef({
    controlled: isControlled,
    onActiveChange,
    onOpenChange,
  });
  callbacksRef.current = {
    controlled: isControlled,
    onActiveChange,
    onOpenChange,
  };

  const carouselIndicatorActive = layout.carousel
    ? activeIndex ?? stateRef.current.carouselIndex
    : null;

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    setIsPlaying(autoplay);
  }, [autoplay]);

  useLayoutEffect(() => {
    const el = stageRef.current;
    if (!el) return;
    const measure = (w: number) => {
      setContainerWidth((prev) =>
        Math.abs(prev - w) < 0.5 ? prev : Math.round(w * 100) / 100
      );
    };
    measure(el.clientWidth);
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) measure(entry.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const targetsFor = useCallback(
    (l: RailLayout, act: number | null, carIdx: number): number[] => {
      const n = shapes.length;
      const widths = shapes.map(
        (s, i) => s.w * l.unit * (i === act ? ACTIVE_EXPAND : 1)
      );
      const gapAfter = (i: number) =>
        l.unit *
        (GAP_FACTOR +
          (act !== null && (i === act || i + 1 === act) ? EXTRA_ACTIVE_GAP : 0));
      const targets = widths.map(() => 0);

      if (l.carousel) {
        const centerIdx = clamp(act ?? carIdx, 0, Math.max(0, n - 1));
        targets[centerIdx] = l.width / 2;
        for (let i = centerIdx + 1; i < n; i++) {
          targets[i] =
            (targets[i - 1] ?? 0) +
            ((widths[i - 1] ?? 0) + (widths[i] ?? 0)) / 2 +
            gapAfter(i - 1);
        }
        for (let i = centerIdx - 1; i >= 0; i--) {
          targets[i] =
            (targets[i + 1] ?? 0) -
            ((widths[i + 1] ?? 0) + (widths[i] ?? 0)) / 2 -
            gapAfter(i);
        }
        return targets;
      }

      let total = 0;
      for (let i = 0; i < n; i++) {
        total += (widths[i] ?? 0) + (i < n - 1 ? gapAfter(i) : 0);
      }
      let curr = (l.width - total) / 2;
      for (let i = 0; i < n; i++) {
        targets[i] = curr + (widths[i] ?? 0) / 2;
        curr += (widths[i] ?? 0) + gapAfter(i);
      }
      return targets;
    },
    [shapes]
  );

  const paint = useCallback((i: number) => {
    const sim = simRef.current;
    const { layout: l, shapes: sh, count: c } = stateRef.current;
    const s = sh[i];
    if (!s) return;

    const fw = s.w * l.unit;
    const posX = sim.x[i] ?? 0;
    const ang = sim.sw[i] ?? 0;
    const liftNorm = clamp(sim.e[i] ?? 0, 0, 1.2);
    const liftActive = clamp(liftNorm, 0, 1);
    const tiltDeg = (sim.ty[i] ?? 0) * liftActive;

    const translate = `translate3d(${(posX - fw / 2).toFixed(2)}px,0,0)`;

    const hang = hangRefs.current[i];
    if (hang) hang.style.transform = translate;

    const shadow = shadowRefs.current[i];
    if (shadow) shadow.style.transform = `${translate} rotate(${ang.toFixed(3)}deg)`;

    const swing = swingRefs.current[i];
    if (swing) swing.style.transform = `rotate(${ang.toFixed(3)}deg)`;

    const tilt = tiltRefs.current[i];
    if (tilt) {
      tilt.style.transform = `perspective(${PERSPECTIVE}px) translateZ(${(
        LIFT_Z * liftNorm
      ).toFixed(2)}px) rotateX(${(TILT_X * liftNorm).toFixed(3)}deg) rotateY(${tiltDeg.toFixed(
        3
      )}deg) scale(${((1 + LIFT_SCALE * liftNorm) / SUPERSAMPLE).toFixed(4)})`;
    }

    const light = lightRefs.current[i];
    if (light) light.style.opacity = liftActive.toFixed(3);

    const wash = washRefs.current[i];
    if (wash) wash.style.opacity = liftActive.toFixed(3);

    const glare = glareRefs.current[i];
    if (glare) {
      glare.style.transform = `translate3d(${(-tiltDeg * 3 - ang * 1.6).toFixed(
        2
      )}%,0,0)`;
    }

    const shadowInner = shadowInnerRefs.current[i];
    if (shadowInner) {
      shadowInner.style.transform = `translate3d(${(-tiltDeg * 1.4).toFixed(
        2
      )}px,${(l.unit * 0.04 + 10 * liftNorm).toFixed(2)}px,0) scale(${(
        1 +
        0.035 * liftNorm
      ).toFixed(4)},${(1 + 0.07 * liftNorm).toFixed(4)})`;
      shadowInner.style.opacity = (1 - 0.3 * liftActive).toFixed(3);
    }

    let otherLift = 0;
    for (let o = 0; o < c; o++) {
      if (o !== i) otherLift = Math.max(otherLift, sim.e[o] ?? 0);
    }
    const dim = dimRefs.current[i];
    if (dim) {
      dim.style.opacity = (0.08 * clamp(otherLift, 0, 1) * (1 - liftActive)).toFixed(
        4
      );
    }
  }, []);

  const step = useCallback(
    (time: number) => {
      const sim = simRef.current;
      const { layout: l, shapes: sh, count: c } = stateRef.current;
      const dt = sim.last ? Math.min(0.1, (time - sim.last) / 1000) : 1 / 60;
      sim.last = time;

      const subSteps = Math.max(3, Math.ceil(dt / 0.0115));
      const subDt = dt / subSteps;
      const pad = CONTACT_EPSILON * l.unit;
      const isFree = time > sim.free;

      for (let s = 0; s < subSteps; s++) {
        for (let i = 0; i < c; i++) {
          const shape = sh[i];
          if (!shape) continue;
          const pendLen = pendulum(l, shape, i);

          if (i !== sim.drag) {
            const vx = sim.vx[i] ?? 0;
            const kSpring = isFree ? 130 : 0;
            const kDamp = isFree ? 2 * Math.sqrt(130) * 0.86 : 3.2;
            const ax = -kSpring * ((sim.x[i] ?? 0) - (sim.tx[i] ?? 0)) - kDamp * vx;
            sim.vx[i] = vx + ax * subDt;
            sim.x[i] = (sim.x[i] ?? 0) + (sim.vx[i] ?? 0) * subDt;
          }

          const ae =
            -150 * ((sim.e[i] ?? 0) - (sim.te[i] ?? 0)) -
            2 * Math.sqrt(150) * 0.78 * (sim.ve[i] ?? 0);
          sim.ve[i] = (sim.ve[i] ?? 0) + ae * subDt;
          sim.e[i] = (sim.e[i] ?? 0) + (sim.ve[i] ?? 0) * subDt;

          const aty =
            -110 * ((sim.ty[i] ?? 0) - (sim.tty[i] ?? 0)) -
            2 * Math.sqrt(110) * 0.72 * (sim.vty[i] ?? 0);
          sim.vty[i] = (sim.vty[i] ?? 0) + aty * subDt;
          sim.ty[i] = (sim.ty[i] ?? 0) + (sim.vty[i] ?? 0) * subDt;

          const targetAngle = restTilt(i) * (1 - clamp(sim.e[i] ?? 0, 0, 1));
          const asw =
            -(GRAVITY_CONST / pendLen) * ((sim.sw[i] ?? 0) - targetAngle) -
            PENDULUM_DAMPING * (sim.vsw[i] ?? 0);
          sim.vsw[i] = (sim.vsw[i] ?? 0) + asw * subDt;
          sim.sw[i] = clamp(
            (sim.sw[i] ?? 0) + (sim.vsw[i] ?? 0) * subDt,
            -SWING_MAX_DEG,
            SWING_MAX_DEG
          );
        }
        resolveContacts(sim, l, sh, pad);
      }

      const smooth = 1 - Math.exp(-dt / 0.035);
      for (let i = 0; i < c; i++) {
        const shape = sh[i];
        const curX = sim.x[i] ?? 0;
        const prevHv = sim.hv[i] ?? 0;
        const newHv = prevHv + ((curX - (sim.hx[i] ?? curX)) / dt - prevHv) * smooth;
        sim.hx[i] = curX;
        sim.hv[i] = newHv;
        if (shape) {
          sim.vsw[i] =
            (sim.vsw[i] ?? 0) +
            clamp(
              (newHv - prevHv) *
                (DEG_TO_RAD / pendulum(l, shape, i)) *
                (i === sim.drag ? FREE_SWING_GAIN : DRAG_SWING_GAIN),
              -40,
              40
            );
        }
      }

      if (sim.drag >= 0) {
        sim.vx[sim.drag] = sim.hv[sim.drag] ?? 0;
      }

      let activeMotion = sim.drag >= 0 || time < sim.free;
      for (let i = 0; i < c; i++) {
        paint(i);
        const targetAng = restTilt(i) * (1 - clamp(sim.e[i] ?? 0, 0, 1));
        if (
          Math.abs(sim.vx[i] ?? 0) > 0.4 ||
          (isFree && Math.abs((sim.x[i] ?? 0) - (sim.tx[i] ?? 0)) > 0.25) ||
          Math.abs((sim.e[i] ?? 0) - (sim.te[i] ?? 0)) > 0.002 ||
          Math.abs(sim.ve[i] ?? 0) > 0.01 ||
          Math.abs((sim.ty[i] ?? 0) - (sim.tty[i] ?? 0)) > 0.02 ||
          Math.abs(sim.vty[i] ?? 0) > 0.05 ||
          Math.abs((sim.sw[i] ?? 0) - targetAng) > 0.02 ||
          Math.abs(sim.vsw[i] ?? 0) > 0.05
        ) {
          activeMotion = true;
        }
      }

      if (activeMotion) {
        sim.raf = requestAnimationFrame(step);
      } else {
        sim.raf = 0;
        sim.last = 0;
        for (let i = 0; i < c; i++) {
          if (isFree) sim.x[i] = sim.tx[i] ?? 0;
          sim.hx[i] = sim.x[i] ?? 0;
          sim.hv[i] = 0;
          sim.vx[i] = 0;
          sim.e[i] = sim.te[i] ?? 0;
          sim.ve[i] = 0;
          sim.ty[i] = sim.tty[i] ?? 0;
          sim.vty[i] = 0;
          sim.sw[i] = restTilt(i) * (1 - clamp(sim.e[i] ?? 0, 0, 1));
          sim.vsw[i] = 0;
          paint(i);
        }
      }
    },
    [paint]
  );

  const kick = useCallback(() => {
    const sim = simRef.current;
    if (stateRef.current.reduced) {
      for (let i = 0; i < stateRef.current.count; i++) {
        sim.x[i] = sim.tx[i] ?? 0;
        sim.vx[i] = 0;
        sim.hx[i] = sim.x[i] ?? 0;
        sim.hv[i] = 0;
        sim.e[i] = sim.te[i] ?? 0;
        sim.ve[i] = 0;
        sim.ty[i] = sim.tty[i] ?? 0;
        sim.vty[i] = 0;
        sim.sw[i] = restTilt(i) * (1 - clamp(sim.e[i] ?? 0, 0, 1));
        sim.vsw[i] = 0;
        paint(i);
      }
      return;
    }
    if (!sim.raf) {
      sim.last = 0;
      sim.raf = requestAnimationFrame(step);
    }
  }, [paint, step]);

  const impulse = useCallback(
    (index: number, degVelocity: number) => {
      const sim = simRef.current;
      if (
        stateRef.current.reduced ||
        index < 0 ||
        index >= stateRef.current.count
      )
        return;
      sim.vsw[index] = (sim.vsw[index] ?? 0) + degVelocity;
      kick();
    },
    [kick]
  );

  useLayoutEffect(() => {
    if (!layout.width) return;
    const sim = simRef.current;
    const tgts = targetsFor(layout, activeIndex, stateRef.current.carouselIndex);
    const countChanged = sim.x.length !== count;

    for (let i = 0; i < count; i++) {
      sim.tx[i] = (tgts[i] ?? 0) + (layout.carousel ? pointerState.current.swipe : 0);
      sim.te[i] = i === activeIndex ? 1 : 0;
      if (i !== activeIndex) sim.tty[i] = 0;

      if (countChanged || reducedMotion) {
        sim.x[i] = sim.tx[i] ?? 0;
        sim.vx[i] = 0;
        sim.hx[i] = sim.x[i] ?? 0;
        sim.hv[i] = 0;
        sim.e[i] = sim.te[i] ?? 0;
        sim.ve[i] = 0;
        sim.ty[i] = sim.tty[i] ?? 0;
        sim.vty[i] = 0;
        sim.sw[i] = restTilt(i) * (1 - (sim.e[i] ?? 0));
        sim.vsw[i] = 0;
      }
    }

    if (countChanged) {
      for (const arr of [
        sim.x,
        sim.vx,
        sim.tx,
        sim.sw,
        sim.vsw,
        sim.e,
        sim.ve,
        sim.te,
        sim.ty,
        sim.vty,
        sim.tty,
        sim.hx,
        sim.hv,
      ]) {
        arr.length = count;
      }
    }

    for (let i = 0; i < count; i++) paint(i);
    kick();
  }, [layout, activeIndex, count, reducedMotion, targetsFor, paint, kick]);

  const prevActiveRef = useRef<number | null>(null);
  useEffect(() => {
    const prev = prevActiveRef.current;
    prevActiveRef.current = activeIndex;
    lastActiveRef.current = undefined;

    if (prev !== activeIndex) {
      if (activeIndex !== null) {
        stateRef.current.carouselIndex = activeIndex;
        impulse(activeIndex - 1, IMPULSE_FORCE);
        impulse(activeIndex + 1, -IMPULSE_FORCE);
      }
      if (prev !== null) {
        impulse(prev - 1, -IMPULSE_FORCE * 0.5);
        impulse(prev + 1, IMPULSE_FORCE * 0.5);
      }
    }
  }, [activeIndex, impulse]);

  const startupRef = useRef({ done: false, timers: [] as number[] });
  useEffect(() => {
    const st = startupRef.current;
    if (!layout.width || st.done || reducedMotion) return;
    st.done = true;
    for (let i = 0; i < count; i++) {
      st.timers.push(
        window.setTimeout(
          () => impulse(i, 18 - i * 1.2),
          140 + i * 60
        )
      );
    }
  }, [layout.width, reducedMotion, count, impulse]);

  useEffect(
    () => () => {
      const st = startupRef.current;
      st.timers.forEach((t) => window.clearTimeout(t));
      st.timers = [];
      st.done = false;
    },
    []
  );

  useEffect(
    () => () => {
      cancelAnimationFrame(simRef.current.raf);
      simRef.current.raf = 0;
    },
    []
  );

  useLayoutEffect(() => {
    if (openIndex !== null || liftHiddenIndex !== null || triggerFocusIndex.current === null)
      return;
    const idx = triggerFocusIndex.current;
    triggerFocusIndex.current = null;
    buttonRefs.current[idx]?.focus({ preventScroll: true });
  }, [openIndex, liftHiddenIndex]);

  const setActive = useCallback((idx: number | null) => {
    if (
      idx === stateRef.current.active ||
      idx === lastActiveRef.current
    )
      return;
    lastActiveRef.current = idx;
    if (!callbacksRef.current.controlled) {
      setUncontrolledActive(idx);
    }
    callbacksRef.current.onActiveChange?.(idx);
  }, []);

  const pauseAutoplay = useCallback(() => setIsPlaying(false), []);

  const autoplayNextTime = useRef(0);
  useEffect(() => {
    if (!isPlaying || reducedMotion || openIndex !== null || count === 0 || !layout.width) {
      autoplayNextTime.current = 0;
      return;
    }
    const now = performance.now();
    if (!autoplayNextTime.current || autoplayNextTime.current < now - interval) {
      autoplayNextTime.current = now + (activeIndex === null ? 1100 : interval);
    }

    let timer: number = window.setTimeout(function advance() {
      const curr = stateRef.current.active;
      autoplayNextTime.current += interval;
      setActive(
        curr === null
          ? stateRef.current.layout.carousel
            ? stateRef.current.carouselIndex
            : 0
          : (curr + 1) % stateRef.current.count
      );
      timer = window.setTimeout(advance, Math.max(0, autoplayNextTime.current - performance.now()));
    }, Math.max(0, autoplayNextTime.current - now));

    return () => window.clearTimeout(timer);
  }, [isPlaying, reducedMotion, openIndex, count, interval, layout.width, setActive, activeIndex]);

  const openDetail = useCallback(
    (idx: number) => {
      pauseAutoplay();
      setActive(idx);
      setOpenIndex(idx);
      callbacksRef.current.onOpenChange?.(idx);
    },
    [setActive, pauseAutoplay]
  );

  const getSourceRect = useCallback(() => {
    if (openIndex === null) return null;
    return tiltRefs.current[openIndex]?.getBoundingClientRect() ?? null;
  }, [openIndex]);

  const handleLiftHidden = useCallback(
    (hidden: boolean) => setLiftHiddenIndex(hidden ? openIndex : null),
    [openIndex]
  );

  const closeDetail = useCallback(() => {
    const idx = openIndex;
    if (idx !== null) {
      triggerFocusIndex.current = idx;
      setOpenIndex(null);
      callbacksRef.current.onOpenChange?.(null);
      impulse(idx, idx % 2 ? 22 : -22);
    }
  }, [openIndex, impulse]);

  function nearestIndex(clientX: number, clientY: number): number | null {
    const el = stageRef.current;
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const relX = clientX - rect.left;
    const relY = clientY - rect.top;
    const { layout: l, shapes: sh, count: c } = stateRef.current;
    const sim = simRef.current;

    let best: number | null = null;
    let bestDist = Infinity;

    for (let i = 0; i < c; i++) {
      const s = sh[i];
      if (!s) continue;
      const [leftReach, rightReach] = reach(sim, l, s, i);
      const cx = sim.x[i] ?? 0;
      const bottom = (l.tops[i] ?? 0) + s.h * l.unit + 30;

      if (
        relX < cx + leftReach - 4 ||
        relX > cx + rightReach + 4 ||
        relY < l.railTop - 4 ||
        relY > bottom
      ) {
        continue;
      }
      const dist = Math.abs(relX - cx);
      if (dist < bestDist) {
        best = i;
        bestDist = dist;
      }
    }
    return best;
  }

  function aim(index: number, clientX: number): void {
    const el = stageRef.current;
    const shape = stateRef.current.shapes[index];
    if (!el || !shape) return;
    const sim = simRef.current;
    const relX = clientX - el.getBoundingClientRect().left;
    const halfW = (shape.w * stateRef.current.layout.unit) / 2;
    for (let i = 0; i < stateRef.current.count; i++) {
      sim.tty[i] =
        i === index ? clamp((relX - (sim.x[index] ?? 0)) / halfW, -1, 1) * AIM_MAX_DEG : 0;
    }
    kick();
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const ptr = pointerState.current;
    const sim = simRef.current;
    const el = stageRef.current;
    const l = stateRef.current.layout;

    if (ptr.id === e.pointerId && el) {
      const dx = e.clientX - ptr.x;
      const t = stamp(e);
      if (
        !ptr.moved &&
        Math.abs(dx) > 6 &&
        Math.abs(dx) > Math.abs(e.clientY - ptr.y)
      ) {
        ptr.moved = true;
        pauseAutoplay();
        if (el.isConnected) el.setPointerCapture(e.pointerId);
        if (!l.carousel && ptr.index >= 0) {
          sim.drag = ptr.index;
          sim.grab = e.clientX - el.getBoundingClientRect().left - (sim.x[ptr.index] ?? 0);
        }
      }
      if (ptr.moved) {
        const vel = (e.clientX - ptr.lastX) / Math.max(1, t - ptr.lastT);
        ptr.v = ptr.v * 0.6 + vel * 0.4;
        ptr.lastX = e.clientX;
        ptr.lastT = t;

        if (sim.drag >= 0) {
          sim.x[sim.drag] = e.clientX - el.getBoundingClientRect().left - sim.grab;
          sim.free = t + 900;
          kick();
        } else if (l.carousel) {
          ptr.swipe = dx;
          const tgts = targetsFor(
            l,
            stateRef.current.active,
            stateRef.current.carouselIndex
          );
          for (let i = 0; i < stateRef.current.count; i++) {
            sim.tx[i] = (tgts[i] ?? 0) + dx;
          }
          kick();
        }
      }
      return;
    }

    if (e.pointerType !== "mouse" || l.carousel || stateRef.current.openIndex !== null)
      return;

    const near = nearestIndex(e.clientX, e.clientY);
    const currAct = stateRef.current.active;
    if (currAct !== null && near !== currAct && el) {
      const s = stateRef.current.shapes[currAct];
      const stageRect = el.getBoundingClientRect();
      const localX = e.clientX - stageRect.left;
      if (
        s &&
        Math.abs(localX - (sim.x[currAct] ?? 0)) <
          (s.w * l.unit * ACTIVE_EXPAND) / 2 + 10 &&
        e.clientY - stageRect.top < l.stageH
      ) {
        aim(currAct, e.clientX);
        return;
      }
    }

    if (near !== null) {
      pauseAutoplay();
      setActive(near);
      aim(near, e.clientX);
    }
  };

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    const near = nearestIndex(e.clientX, e.clientY);
    const t = stamp(e);
    tapTargetIndex.current = -1;
    pointerState.current = {
      id: e.pointerId,
      index: near ?? -1,
      x: e.clientX,
      y: e.clientY,
      moved: false,
      kind: e.pointerType,
      swipe: 0,
      lastX: e.clientX,
      lastT: t,
      v: 0,
    };
  };

  const finishPointer = (e: React.PointerEvent, cancelled: boolean) => {
    const ptr = pointerState.current;
    if (ptr.id !== e.pointerId) return;

    const sim = simRef.current;
    const el = stageRef.current;
    if (el?.hasPointerCapture(e.pointerId)) {
      el.releasePointerCapture(e.pointerId);
    }
    pointerState.current = { ...ptr, id: -1 };

    if (sim.drag >= 0) {
      const dt = stamp(e) - ptr.lastT;
      sim.vx[sim.drag] = dt < 140 ? ptr.v * 1000 * (1 - dt / 140) : 0;
      sim.drag = -1;
      sim.free = performance.now() + 700;
      kick();
      return;
    }

    const l = stateRef.current.layout;
    if (ptr.moved && l.carousel) {
      const dist = e.clientX - ptr.x;
      const currentActive = stateRef.current.active ?? stateRef.current.carouselIndex;
      const stepDirection =
        Math.abs(dist) > 40 || Math.abs(ptr.v) > 0.45 ? (dist < 0 ? 1 : -1) : 0;
      pointerState.current.swipe = 0;
      const nextIdx = clamp(currentActive + stepDirection, 0, stateRef.current.count - 1);
      stateRef.current.carouselIndex = nextIdx;
      if (nextIdx === stateRef.current.active || isControlled) {
        const tgts = targetsFor(l, isControlled ? stateRef.current.active : nextIdx, nextIdx);
        for (let i = 0; i < stateRef.current.count; i++) sim.tx[i] = tgts[i] ?? 0;
        kick();
      }
      setActive(nextIdx);
      return;
    }

    if (!cancelled && !ptr.moved && ptr.index >= 0) {
      pauseAutoplay();
      if (
        (ptr.kind !== "mouse" || l.carousel) &&
        stateRef.current.active !== ptr.index
      ) {
        setActive(ptr.index);
      } else {
        tapTargetIndex.current = ptr.index;
      }
    }
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    pauseAutoplay();
    const curr = activeIndex ?? focusIndex;
    const next =
      e.key === "Home"
        ? 0
        : e.key === "End"
        ? count - 1
        : clamp(curr + (e.key === "ArrowRight" ? 1 : -1), 0, count - 1);
    setFocusIndex(next);
    setActive(next);
    buttonRefs.current[next]?.focus({ preventScroll: true });
  };

  const activeItem = activeIndex === null ? null : items[activeIndex];
  const metaText = activeItem
    ? [[activeItem.artist, activeItem.year].filter(Boolean).join(", "), activeItem.tag]
        .filter(Boolean)
        .join(" · ")
    : "";
  const unitPx = layout.unit;
  const shadowBlur = Math.max(3, unitPx * 0.05);

  return (
    <section
      {...props}
      data-slot="picture-rail-gallery"
      data-mode={layout.carousel ? "carousel" : "rail"}
      data-active={activeIndex ?? ""}
      aria-roledescription="picture rail gallery"
      className={`relative isolate w-full overflow-hidden bg-background text-foreground ${
        className ?? ""
      }`}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(72% 58% at 50% 44%, color-mix(in oklab, var(--color-foreground) 4%, transparent), transparent 78%)",
        }}
      />

      {(eyebrow || heading) && (
        <header className="relative z-10 flex flex-col items-center gap-2 px-6 pt-7 text-center">
          {eyebrow && (
            <p className="text-[11px] font-medium uppercase tracking-[0.28em] text-muted-foreground">
              {eyebrow}
            </p>
          )}
          {heading && (
            <h2 className="text-balance text-2xl font-medium tracking-tight sm:text-3xl">
              {heading}
            </h2>
          )}
        </header>
      )}

      <div
        ref={stageRef}
        data-stage
        role="group"
        aria-label={heading ?? "Picture rail"}
        className="relative mt-5 w-full touch-pan-y select-none"
        style={{ height: layout.stageH, overflowX: "clip" }}
        onPointerMove={onPointerMove}
        onPointerDown={onPointerDown}
        onPointerUp={(e) => finishPointer(e, false)}
        onPointerCancel={(e) => finishPointer(e, true)}
        onPointerLeave={(e) => {
          if (
            e.pointerType !== "mouse" ||
            pointerState.current.id >= 0 ||
            layout.carousel
          )
            return;
          for (let i = 0; i < count; i++) simRef.current.tty[i] = 0;
          if (!document.activeElement?.matches("[data-frame]:focus-visible")) {
            setActive(null);
          }
          kick();
        }}
        onKeyDown={onKeyDown}
      >
        {/* Brass rail */}
        <div
          aria-hidden="true"
          data-rail
          className="pointer-events-none absolute inset-x-0 z-[1]"
          style={{ top: layout.railTop, height: layout.railT }}
        >
          <div className="absolute inset-x-0 top-full h-3 bg-black opacity-[0.07] blur-[5px] dark:opacity-40" />
          <div
            className="absolute inset-0"
            style={{
              background:
                "linear-gradient(to bottom, color-mix(in oklab, var(--color-card) 70%, white) 0%, var(--color-card) 16%, color-mix(in oklab, var(--color-card) 90%, black) 30%, color-mix(in oklab, var(--color-card) 96%, white) 46%, var(--color-card) 62%, color-mix(in oklab, var(--color-card) 84%, black) 86%, color-mix(in oklab, var(--color-card) 72%, black) 100%)",
              boxShadow:
                "0 1px 0 color-mix(in oklab, var(--color-foreground) 14%, transparent), 0 -1px 0 color-mix(in oklab, var(--color-foreground) 8%, transparent)",
            }}
          />
          <div className="absolute inset-x-0 top-[30%] h-px bg-black opacity-10 dark:opacity-40" />
          <div className="absolute inset-x-0 top-0 h-px bg-white opacity-80 dark:opacity-15" />
        </div>

        {/* Ambient shadows / lights */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 z-[2]"
        >
          {items.map((item, i) => {
            const sh = shapes[i];
            if (!sh) return null;
            const fw = sh.w * unitPx;
            const fh = sh.h * unitPx;
            const topY = layout.tops[i] ?? 0;
            return (
              <div
                key={item.id}
                ref={(el) => {
                  shadowRefs.current[i] = el;
                }}
                className="absolute left-0 top-0"
                style={{
                  width: fw,
                  height: 0,
                  transformOrigin: `${fw / 2}px ${layout.pivotY + 1}px`,
                  visibility: liftHiddenIndex === i ? "hidden" : undefined,
                }}
              >
                <span
                  ref={(el) => {
                    washRefs.current[i] = el;
                  }}
                  data-wash
                  className="absolute opacity-0 [--wash:color-mix(in_oklab,gold_28%,transparent)] dark:[--wash:color-mix(in_oklab,gold_30%,transparent)]"
                  style={{
                    left: -fw * 0.5,
                    width: fw * 2,
                    top: topY - fh * 0.5,
                    height: fh * 1.75,
                    background: "radial-gradient(closest-side, var(--wash), transparent)",
                  }}
                />
                <span
                  className="absolute opacity-[0.22] dark:opacity-70"
                  style={{
                    left: 0,
                    top: topY,
                    width: fw,
                    height: fh,
                    filter: `blur(${shadowBlur.toFixed(1)}px)`,
                  }}
                >
                  <span
                    ref={(el) => {
                      shadowInnerRefs.current[i] = el;
                    }}
                    className="absolute inset-0 rounded-[2px] bg-black"
                  />
                </span>
              </div>
            );
          })}
        </div>

        {/* Hanging frames */}
        {items.map((item, i) => {
          const sh = shapes[i];
          if (!sh) return null;
          const fw = sh.w * unitPx;
          const fh = sh.h * unitPx;
          const topY = layout.tops[i] ?? 0;
          const isAct = activeIndex === i;
          const wireTargetY = topY + fh * 0.07;

          return (
            <div
              key={item.id}
              ref={(el) => {
                hangRefs.current[i] = el;
              }}
              data-hang={i}
              className="pointer-events-none absolute left-0 top-0"
              style={{
                width: fw,
                height: 0,
                zIndex: isAct ? 30 : 10 + i,
              }}
            >
              <Hook
                x={fw / 2}
                railTop={layout.railTop}
                railT={layout.railT}
                pivotY={layout.pivotY}
              />

              {item.tag && (
                <span
                  data-label
                  className={`absolute whitespace-nowrap rounded-[3px] border border-border bg-card px-1.5 py-[3px] text-[10px] font-medium leading-none tabular-nums shadow-[0_1px_2px_color-mix(in_oklab,var(--color-foreground)_10%,transparent)] ${
                    isAct ? "text-card-foreground" : "text-muted-foreground"
                  }`}
                  style={{ top: topY + fh + 10, right: 0 }}
                >
                  {isAct && (
                    <span
                      aria-hidden="true"
                      className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-chart-2 align-middle"
                    />
                  )}
                  {item.tag}
                </span>
              )}

              <span
                ref={(el) => {
                  swingRefs.current[i] = el;
                }}
                data-swing
                className="absolute left-0 top-0"
                style={{
                  width: fw,
                  height: 0,
                  transformOrigin: `${fw / 2}px ${layout.pivotY + 1}px`,
                  visibility: liftHiddenIndex === i ? "hidden" : undefined,
                }}
              >
                {/* Steel hanging wires */}
                <svg
                  aria-hidden="true"
                  className="pointer-events-none absolute left-0 top-0 overflow-visible text-foreground"
                  width={Math.max(1, fw)}
                  height={Math.max(1, wireTargetY)}
                >
                  {[fw * 0.2, fw * 0.8].map((wireX) => (
                    <g key={wireX}>
                      <line
                        x1={fw / 2 + 0.7}
                        y1={layout.pivotY + 1.8}
                        x2={wireX + 0.7}
                        y2={wireTargetY + 0.8}
                        stroke="black"
                        strokeOpacity="0.14"
                        strokeWidth="1.4"
                      />
                      <line
                        x1={fw / 2}
                        y1={layout.pivotY + 1}
                        x2={wireX}
                        y2={wireTargetY}
                        stroke="currentColor"
                        strokeOpacity="0.6"
                        strokeWidth="1"
                      />
                      <line
                        x1={fw / 2 - 0.3}
                        y1={layout.pivotY + 1}
                        x2={wireX - 0.3}
                        y2={wireTargetY}
                        stroke="white"
                        strokeOpacity="0.35"
                        strokeWidth="0.4"
                      />
                    </g>
                  ))}
                </svg>

                <button
                  ref={(el) => {
                    buttonRefs.current[i] = el;
                  }}
                  type="button"
                  data-frame={i}
                  data-lit={isAct || undefined}
                  tabIndex={i === (activeIndex ?? focusIndex) ? 0 : -1}
                  aria-label={item.title}
                  aria-describedby={`${uid}-caption`}
                  aria-pressed={isAct}
                  className="pointer-events-auto absolute cursor-pointer rounded-[2px] outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[6px] focus-visible:outline-ring"
                  style={{
                    left: 0,
                    top: topY,
                    width: fw,
                    height: fh,
                  }}
                  onFocus={() => {
                    setFocusIndex(i);
                    if (pointerState.current.id < 0) {
                      pauseAutoplay();
                      setActive(i);
                    }
                  }}
                  onClick={(e) => {
                    const tapped = tapTargetIndex.current;
                    tapTargetIndex.current = -1;
                    if (e.detail === 0 || tapped === i) {
                      openDetail(i);
                    }
                  }}
                >
                  <span
                    ref={(el) => {
                      tiltRefs.current[i] = el;
                    }}
                    data-tilt
                    className="absolute block"
                    style={{
                      left: (-1 * fw) / 2,
                      top: (-1 * fh) / 2,
                      width: fw * SUPERSAMPLE,
                      height: fh * SUPERSAMPLE,
                      transform: `scale(${1 / SUPERSAMPLE})`,
                    }}
                  >
                    <span
                      className="absolute inset-0 block"
                      style={{ zoom: SUPERSAMPLE }}
                    >
                      <FrameArt
                        item={item}
                        shape={sh}
                        unit={unitPx}
                        lightRef={(el) => {
                          lightRefs.current[i] = el;
                        }}
                        glareRef={(el) => {
                          glareRefs.current[i] = el;
                        }}
                        dimRef={(el) => {
                          dimRefs.current[i] = el;
                        }}
                      />
                    </span>
                  </span>
                </button>
              </span>
            </div>
          );
        })}
      </div>

      {layout.carousel && count > 1 && (
        <div
          className="relative z-10 mt-1 flex justify-center gap-1.5"
          role="group"
          aria-label={heading ?? "Prints"}
        >
          {items.map((item, i) => (
            <button
              key={item.id}
              type="button"
              aria-label={item.title}
              aria-current={carouselIndicatorActive === i}
              onClick={() => {
                pauseAutoplay();
                setActive(i);
              }}
              className={`h-1.5 rounded-full outline-none transition-[width,background-color] duration-300 focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none ${
                carouselIndicatorActive === i
                  ? "w-6 bg-foreground"
                  : "w-1.5 bg-foreground/25 hover:bg-foreground/45"
              }`}
            />
          ))}
        </div>
      )}

      <div className="relative z-10 flex flex-col items-center gap-3 px-6 pb-7 pt-3 text-center">
        <div
          id={`${uid}-caption`}
          aria-live="polite"
          className="min-h-[2.75rem]"
        >
          <p className="text-sm font-medium">
            {activeItem ? activeItem.title : caption}
          </p>
          {activeItem && (
            <p className="mt-0.5 text-[13px] text-muted-foreground">
              {metaText}
              {metaText ? " · " : ""}
              <span className="text-foreground/80">{labels.open}</span>
            </p>
          )}
        </div>
        {action}
      </div>

      {openIndex !== null && items[openIndex] && shapes[openIndex] && (
        <Detail
          uid={uid}
          item={items[openIndex]}
          shape={shapes[openIndex]}
          index={openIndex}
          total={count}
          labels={labels}
          reduced={reducedMotion}
          source={getSourceRect}
          onLift={handleLiftHidden}
          onClose={closeDetail}
        />
      )}
    </section>
  );
}

function Hook({
  x,
  railTop,
  railT,
  pivotY,
}: {
  x: number;
  railTop: number;
  railT: number;
  pivotY: number;
}) {
  const hookW = clamp(railT * 0.36, 3, 6);
  const hookH = pivotY - railTop + 6;
  return (
    <span
      aria-hidden="true"
      className="absolute"
      style={{
        left: x - hookW,
        top: railTop - 3,
        width: hookW * 2,
        height: hookH,
      }}
    >
      <span
        className="absolute inset-x-0 top-0 rounded-full"
        style={{
          height: 4,
          background: BRASS_GRADIENT_HOOK,
          boxShadow: "0 1px 1px color-mix(in oklab, black 30%, transparent)",
        }}
      />
      <span
        className="absolute top-[3px] rounded-b-[1px]"
        style={{
          left: hookW * 0.5,
          width: hookW,
          bottom: 5,
          background: BRASS_GRADIENT_STEM,
          boxShadow: "1px 1px 1.5px color-mix(in oklab, black 28%, transparent)",
        }}
      />
      <svg
        aria-hidden="true"
        className="absolute bottom-0 left-0 overflow-visible"
        width={hookW * 2}
        height={7}
        style={{ color: "color-mix(in oklab, darkgoldenrod 80%, black)" }}
      >
        <path
          d={`M${hookW * 0.62},0 Q${hookW * 0.62},6.2 ${hookW},6.2 Q${
            hookW * 1.38
          },6.2 ${hookW * 1.38},2.4`}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
        />
      </svg>
    </span>
  );
}

function Moulding({
  frame,
  m,
}: {
  frame: "black" | "oak" | "white";
  m: number;
}) {
  const base = FRAME_COLORS[frame];
  const [c0, c1, c2, c3, c4, c5] = FRAME_LIGHTING[frame];
  const sides = [
    {
      key: "t",
      style: {
        left: 0,
        right: 0,
        top: 0,
        height: m,
        clipPath: `polygon(0 0, 100% 0, calc(100% - ${m}px) 100%, ${m}px 100%)`,
      },
      dir: "to bottom",
      along: "178.6deg",
      light: 0.16,
    },
    {
      key: "l",
      style: {
        left: 0,
        top: 0,
        bottom: 0,
        width: m,
        clipPath: `polygon(0 0, 100% ${m}px, 100% calc(100% - ${m}px), 0 100%)`,
      },
      dir: "to right",
      along: "91.2deg",
      light: 0.04,
    },
    {
      key: "r",
      style: {
        right: 0,
        top: 0,
        bottom: 0,
        width: m,
        clipPath: `polygon(0 ${m}px, 100% 0, 100% 100%, 0 calc(100% - ${m}px))`,
      },
      dir: "to left",
      along: "88.9deg",
      light: -0.14,
    },
    {
      key: "b",
      style: {
        left: 0,
        right: 0,
        bottom: 0,
        height: m,
        clipPath: `polygon(${m}px 0, calc(100% - ${m}px) 0, 100% 100%, 0 100%)`,
      },
      dir: "to top",
      along: "1.3deg",
      light: -0.24,
    },
  ];

  return (
    <>
      {sides.map((side) => {
        const bg: string[] = [tone(side.light * c5)];
        if (frame === "oak") {
          bg.push(
            `repeating-linear-gradient(${side.along}, transparent 0 1.7px, color-mix(in oklab, sienna 26%, transparent) 1.7px 2.3px, transparent 2.3px 4.4px, color-mix(in oklab, saddlebrown 16%, transparent) 4.4px 4.9px, transparent 4.9px 7.6px)`
          );
        }
        bg.push(
          `linear-gradient(${side.dir}, ${mix(base, c0)} 0%, ${mix(
            base,
            c1
          )} 16%, ${mix(base, c2)} 32%, ${base} 56%, ${mix(base, c3)} 82%, ${mix(
            base,
            c4
          )} 100%)`
        );
        return (
          <span
            key={side.key}
            aria-hidden="true"
            className="absolute"
            style={{ ...side.style, background: bg.join(", ") }}
          />
        );
      })}
    </>
  );
}

function Fixture({
  width,
  hood,
  arm,
}: {
  width: number;
  hood: number;
  arm: number;
}) {
  return (
    <span
      aria-hidden="true"
      className="pointer-events-none absolute left-1/2 -translate-x-1/2"
      style={{ bottom: "100%", width, height: arm + hood }}
    >
      {[0.26, 0.74].map((frac) => (
        <span
          key={frac}
          className="absolute bottom-0"
          style={{
            left: `calc(${frac * 100}% - 0.75px)`,
            width: 1.5,
            height: arm + hood * 0.5,
            background:
              "linear-gradient(to right, color-mix(in oklab, goldenrod 60%, white), color-mix(in oklab, darkgoldenrod 70%, black))",
          }}
        />
      ))}
      <span
        className="absolute inset-x-0 top-0 rounded-full"
        style={{
          height: hood,
          background: BRASS_GRADIENT_FIXTURE,
          boxShadow: "0 1px 2px color-mix(in oklab, black 35%, transparent)",
        }}
      />
      <span
        className="absolute top-0 rounded-full bg-white opacity-30"
        style={{
          left: "8%",
          right: "8%",
          height: Math.max(1, hood * 0.22),
          marginTop: hood * 0.12,
        }}
      />
    </span>
  );
}

function FrameArt({
  item,
  shape,
  unit,
  lit,
  lightRef,
  glareRef,
  dimRef,
}: {
  item: PictureRailItem;
  shape: FrameShape;
  unit: number;
  lit?: number;
  lightRef?: (el: HTMLSpanElement | null) => void;
  glareRef?: (el: HTMLSpanElement | null) => void;
  dimRef?: (el: HTMLSpanElement | null) => void;
}) {
  const moldW = Math.max(2, shape.mold * unit);
  const matW = shape.mat * unit;
  const matBW = shape.matB * unit;
  const fixtureW = clamp(shape.w * unit * 0.46, 30, 190);
  const fixtureHood = clamp(unit * 0.05, 4, 12);
  const fixtureArm = clamp(unit * 0.07, 5, 20);
  const totalFixtureH = fixtureArm + fixtureHood;
  const bevel = clamp(unit * 0.012, 1, 3);

  return (
    <>
      <Fixture width={fixtureW} hood={fixtureHood} arm={fixtureArm} />

      <span
        className="absolute inset-0 block rounded-[1.5px]"
        style={{
          boxShadow: "0 0 0 0.6px color-mix(in oklab, black 45%, transparent)",
        }}
      >
        <Moulding frame={shape.frame} m={moldW} />

        <span
          className="absolute block overflow-hidden"
          style={{
            inset: moldW,
            background: matW
              ? `linear-gradient(to bottom, ${MAT_COLOR}, color-mix(in oklab, white 89%, wheat))`
              : "var(--color-muted)",
          }}
        >
          <span
            className="absolute block overflow-hidden bg-muted"
            style={{
              backgroundImage:
                "radial-gradient(120% 90% at 28% 18%, color-mix(in oklab, var(--color-foreground) 9%, transparent), transparent 70%)",
              left: matW,
              right: matW,
              top: matW,
              bottom: matW + matBW,
              boxShadow: matW
                ? `0 0 0 ${bevel}px color-mix(in oklab, white 97%, wheat), 0 0 0 ${
                    bevel + 0.6
                  }px color-mix(in oklab, black 16%, transparent), ${
                    bevel * 0.6
                  }px ${bevel}px ${bevel * 1.6}px ${bevel}px color-mix(in oklab, black 9%, transparent)`
                : undefined,
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.image}
              alt=""
              draggable={false}
              decoding="async"
              ref={(el) => {
                if (el?.complete && el.naturalWidth > 0) {
                  el.dataset.loaded = "true";
                }
              }}
              onLoad={(e) => {
                e.currentTarget.dataset.loaded = "true";
              }}
              onError={(e) => {
                e.currentTarget.dataset.failed = "true";
              }}
              className="pointer-events-none absolute inset-0 h-full w-full select-none object-cover opacity-0 transition-opacity duration-500 data-[failed]:hidden data-[loaded]:opacity-100 motion-reduce:transition-none"
            />
          </span>

          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 block"
            style={{
              boxShadow: `inset 0 ${(moldW * 0.45).toFixed(1)}px ${(
                moldW * 0.9
              ).toFixed(1)}px color-mix(in oklab, black 30%, transparent), inset ${(
                moldW * 0.2
              ).toFixed(1)}px 0 ${(moldW * 0.5).toFixed(
                1
              )}px color-mix(in oklab, black 12%, transparent), inset 0 0 0 0.5px color-mix(in oklab, black 45%, transparent)`,
            }}
          />

          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 block overflow-hidden"
          >
            <span
              className="absolute inset-0 block"
              style={{
                background:
                  "linear-gradient(to bottom, color-mix(in oklab, white 9%, transparent), transparent 30%)",
              }}
            />
            <span
              ref={glareRef}
              data-glare
              className="absolute inset-y-0 -left-1/2 block w-[200%]"
              style={{
                background:
                  "linear-gradient(112deg, transparent 37%, color-mix(in oklab, white 10%, transparent) 43.5%, color-mix(in oklab, white 4%, transparent) 50%, transparent 56%)",
              }}
            />
          </span>
        </span>

        {/* Lit cone */}
        <span
          ref={lightRef}
          data-light
          aria-hidden="true"
          className="pointer-events-none absolute block opacity-0 mix-blend-screen"
          style={{
            left: 0,
            right: 0,
            top: -totalFixtureH,
            bottom: 0,
            ...(lit !== undefined ? { opacity: lit } : null),
          }}
        >
          <span
            className="absolute left-1/2 block -translate-x-1/2 rounded-full"
            style={{
              top: 0,
              width: fixtureW,
              height: fixtureHood,
              background: BRASS_GRADIENT_HOOK,
              opacity: 0.55,
            }}
          />
          <span
            className="absolute left-1/2 block -translate-x-1/2 rounded-full"
            style={{
              top: fixtureHood * 0.6,
              width: fixtureW * 0.86,
              height: Math.max(2, fixtureHood * 0.45),
              background: GOLD_LIGHT,
              boxShadow: `0 0 ${(fixtureHood * 1.8).toFixed(1)}px ${(
                fixtureHood * 0.6
              ).toFixed(1)}px color-mix(in oklab, gold 55%, transparent)`,
            }}
          />
          <span
            className="absolute block"
            style={{
              left: moldW * 0.4,
              right: moldW * 0.4,
              top: totalFixtureH - 1,
              height: moldW * 1.8,
              background: `radial-gradient(55% 100% at 50% 0%, color-mix(in oklab, ${GOLD_LIGHT} 75%, transparent), transparent)`,
            }}
          />
          <span
            className="absolute block"
            style={{
              left: moldW,
              right: moldW,
              top: totalFixtureH + moldW * 0.2,
              bottom: moldW,
              background: `radial-gradient(95% 78% at 50% 0%, color-mix(in oklab, ${GOLD_LIGHT} 50%, transparent) 0%, color-mix(in oklab, ${GOLD_LIGHT} 18%, transparent) 46%, transparent 80%)`,
            }}
          />
        </span>

        <span
          ref={dimRef}
          data-dim
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 block bg-black opacity-0"
        />
      </span>
    </>
  );
}

function FrameBack({
  item,
  shape,
  unit,
}: {
  item: PictureRailItem;
  shape: FrameShape;
  unit: number;
}) {
  const fw = shape.w * unit;
  const fh = shape.h * unit;
  const moldW = Math.max(4, shape.mold * unit * 0.85);
  const innerW = fw - moldW * 2;
  const innerH = fh - moldW * 2;
  const tapeW = clamp(unit * 0.035, 4, 12);
  const wireH = innerH * 0.24;
  const eyeletX = [innerW * 0.16, innerW * 0.84];
  const wireDip = wireH + innerH * 0.13;
  const labelFont = clamp(unit * 0.034, 8.5, 13);

  return (
    <div
      className="absolute inset-0 overflow-hidden rounded-[2px]"
      style={{
        background:
          "repeating-linear-gradient(90.6deg, transparent 0 3px, color-mix(in oklab, sienna 12%, transparent) 3px 3.6px, transparent 3.6px 8px), linear-gradient(to bottom, color-mix(in oklab, burlywood 70%, white), color-mix(in oklab, burlywood 85%, sienna))",
        boxShadow: "inset 0 0 0 0.6px color-mix(in oklab, black 40%, transparent)",
      }}
    >
      <div
        className="absolute"
        style={{
          inset: moldW,
          background:
            "repeating-linear-gradient(33deg, transparent 0 2.6px, color-mix(in oklab, sienna 7%, transparent) 2.6px 3.4px), repeating-linear-gradient(-61deg, transparent 0 4px, color-mix(in oklab, white 6%, transparent) 4px 4.8px), linear-gradient(160deg, color-mix(in oklab, tan 82%, white), color-mix(in oklab, tan 70%, sienna))",
          boxShadow: `inset 0 0 0 ${tapeW}px color-mix(in oklab, peru 52%, tan), inset 0 0 0 ${
            tapeW + 0.6
          }px color-mix(in oklab, sienna 30%, transparent), 0 0 0 0.5px color-mix(in oklab, black 30%, transparent)`,
        }}
      >
        <svg
          aria-hidden="true"
          className="absolute inset-0 overflow-visible"
          width={innerW}
          height={innerH}
        >
          <path
            d={`M${eyeletX[0]},${wireH + 5} Q${innerW / 2},${wireDip + 10} ${
              eyeletX[1]
            },${wireH + 5}`}
            fill="none"
            stroke="color-mix(in oklab, black 30%, transparent)"
            strokeWidth="2.2"
            transform="translate(0.8 1.4)"
          />
          <path
            d={`M${eyeletX[0]},${wireH + 5} Q${innerW / 2},${wireDip + 10} ${
              eyeletX[1]
            },${wireH + 5}`}
            fill="none"
            stroke="color-mix(in oklab, gray 70%, white)"
            strokeWidth="1.6"
          />
          <path
            d={`M${eyeletX[0]},${wireH + 5} Q${innerW / 2},${wireDip + 10} ${
              eyeletX[1]
            },${wireH + 5}`}
            fill="none"
            stroke="white"
            strokeOpacity="0.55"
            strokeWidth="0.5"
            strokeDasharray="1.2 1.6"
          />
          {eyeletX.map((ex, idx) => (
            <g key={ex}>
              <path
                d={`M${ex + (idx ? -4 : 4)},${wireH + 5} l${
                  idx ? -9 : 9
                },2.2 l${idx ? 1.6 : -1.6},1.4 l${idx ? -8 : 8},1.6`}
                fill="none"
                stroke="color-mix(in oklab, gray 60%, white)"
                strokeWidth="1.1"
                strokeLinecap="round"
              />
              <rect
                x={ex - 5}
                y={wireH - 9}
                width="10"
                height="13"
                rx="2"
                fill="color-mix(in oklab, gray 55%, white)"
                stroke="color-mix(in oklab, black 35%, transparent)"
                strokeWidth="0.6"
              />
              <circle
                cx={ex}
                cy={wireH - 5}
                r="1.5"
                fill="color-mix(in oklab, gray 70%, black)"
              />
              <circle
                cx={ex}
                cy={wireH + 0.4}
                r="1.5"
                fill="color-mix(in oklab, gray 70%, black)"
              />
              <path
                d={`M${ex - 4.5},${wireH + 3} Q${ex - 4.5},${wireH + 10} ${ex},${
                  wireH + 10
                } Q${ex + 4.5},${wireH + 10} ${ex + 4.5},${wireH + 3}`}
                fill="none"
                stroke="color-mix(in oklab, gray 45%, white)"
                strokeWidth="2"
              />
              <path
                d={`M${ex - 4.5},${wireH + 3} Q${ex - 4.5},${wireH + 10} ${ex},${
                  wireH + 10
                } Q${ex + 4.5},${wireH + 10} ${ex + 4.5},${wireH + 3}`}
                fill="none"
                stroke="white"
                strokeOpacity="0.6"
                strokeWidth="0.6"
              />
            </g>
          ))}
          {[
            [tapeW * 2.2, innerH - tapeW * 2.2],
            [innerW - tapeW * 2.2, innerH - tapeW * 2.2],
          ].map(([bx, by]) => (
            <g key={`${bx}-${by}`}>
              <circle
                cx={bx}
                cy={by}
                r={clamp(unit * 0.03, 3, 7)}
                fill="color-mix(in oklab, black 70%, white)"
              />
              <circle
                cx={(bx ?? 0) - 0.8}
                cy={(by ?? 0) - 0.9}
                r={clamp(unit * 0.012, 1, 2.6)}
                fill="white"
                fillOpacity="0.35"
              />
            </g>
          ))}
        </svg>

        <div
          data-back-label
          className="absolute left-1/2 -translate-x-1/2 rounded-[2px] text-left"
          style={{
            bottom: innerH * 0.14,
            width: clamp(innerW * 0.66, 120, 300),
            padding: `${labelFont * 0.8}px ${labelFont}px`,
            fontSize: labelFont,
            lineHeight: 1.35,
            background: MAT_COLOR,
            color: LABEL_TEXT,
            boxShadow:
              "0 1px 2px color-mix(in oklab, black 25%, transparent), inset 0 0 0 0.5px color-mix(in oklab, black 12%, transparent)",
          }}
        >
          <p
            className="uppercase"
            style={{ fontSize: "0.7em", letterSpacing: "0.2em", opacity: 0.6 }}
          >
            Gallery label
          </p>
          <p
            className="font-semibold"
            style={{ fontSize: "1.18em", marginTop: "0.25em" }}
          >
            {item.title}
          </p>
          {(item.artist || item.year) && (
            <p>{[item.artist, item.year].filter(Boolean).join(", ")}</p>
          )}
          {item.details && item.details.length > 0 && (
            <ul
              className="mt-[0.35em] border-t pt-[0.35em]"
              style={{
                borderColor: "color-mix(in oklab, black 14%, transparent)",
              }}
            >
              {item.details.map((dt) => (
                <li key={dt}>{dt}</li>
              ))}
            </ul>
          )}
          <svg
            aria-hidden="true"
            viewBox="0 0 120 26"
            className="mt-[0.3em] block h-[1.9em] w-auto"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3,18 C10,4 14,4 13,14 C12,22 18,20 22,12 C25,6 27,8 26,15 C30,10 34,9 35,15 C37,21 43,6 48,9 C52,12 47,20 54,17 C60,14 63,7 66,12 C69,18 74,14 79,11 C84,8 88,16 94,13 C100,10 106,11 116,8" />
          </svg>
        </div>
      </div>
    </div>
  );
}

function fitUnit(shape: FrameShape): number {
  if (typeof window === "undefined") return 280;
  const isMd = window.innerWidth >= 768;
  const maxW = isMd
    ? Math.min(520, window.innerWidth * 0.46)
    : window.innerWidth * 0.78;
  const maxH = isMd
    ? Math.min(500, window.innerHeight * 0.64)
    : window.innerHeight * 0.4;
  return Math.max(80, Math.min(maxW / shape.w, maxH / shape.h));
}

function Detail({
  uid,
  item,
  shape,
  index,
  total,
  labels,
  reduced,
  source,
  onLift,
  onClose,
}: {
  uid: string;
  item: PictureRailItem;
  shape: FrameShape;
  index: number;
  total: number;
  labels: { front?: string; back?: string; close?: string; open?: string };
  reduced: boolean;
  source: () => DOMRect | null;
  onLift: (hidden: boolean) => void;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const figureRef = useRef<HTMLDivElement>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const [face, setFace] = useState<"front" | "back">("front");
  const [mounted, setMounted] = useState(false);
  const [detailUnit, setDetailUnit] = useState(() => fitUnit(shape));

  const rotRef = useRef({
    value: 0,
    target: 0,
    velocity: 0,
    raf: 0,
    last: 0,
    dragging: false,
    startX: 0,
    startAngle: 0,
  });
  const isClosingRef = useRef(false);
  const titleId = `${uid}-detail-title`;

  useEffect(() => {
    const handleResize = () => setDetailUnit(fitUnit(shape));
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [shape]);

  const loopFlip = useCallback(() => {
    const rot = rotRef.current;
    const cardEl = cardRef.current;
    const tick = (time: number) => {
      const dt = rot.last ? Math.min(0.1, (time - rot.last) / 1000) : 1 / 60;
      rot.last = time;
      const sub = Math.ceil(dt / 0.012);
      for (let s = 0; s < sub; s++) {
        const acc =
          -90 * (rot.value - rot.target) - 2 * Math.sqrt(90) * 0.82 * rot.velocity;
        rot.velocity += (acc * dt) / sub;
        rot.value += (rot.velocity * dt) / sub;
      }
      if (cardEl) cardEl.style.transform = `rotateY(${rot.value.toFixed(2)}deg)`;
      if (
        Math.abs(rot.value - rot.target) < 0.05 &&
        Math.abs(rot.velocity) < 0.05
      ) {
        rot.value = rot.target;
        if (cardEl) cardEl.style.transform = `rotateY(${rot.value}deg)`;
        rot.raf = 0;
        rot.last = 0;
        return;
      }
      rot.raf = requestAnimationFrame(tick);
    };

    if (reduced) {
      rot.value = rot.target;
      if (cardEl) cardEl.style.transform = `rotateY(${rot.value}deg)`;
      return;
    }
    if (!rot.raf) rot.raf = requestAnimationFrame(tick);
  }, [reduced]);

  const flipTo = useCallback(
    (targetFace: "front" | "back") => {
      const rot = rotRef.current;
      const baseTurn = Math.round(rot.value / 360) * 360;
      rot.target = baseTurn + (targetFace === "back" ? 180 : 0);
      if (Math.abs(rot.target - rot.value) > 180) {
        rot.target -= 360 * Math.sign(rot.target - rot.value);
      }
      setFace(targetFace);
      loopFlip();
    },
    [loopFlip]
  );

  useLayoutEffect(() => {
    const fig = figureRef.current;
    const srcRect = source();
    closeBtnRef.current?.focus({ preventScroll: true });

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    let anim: Animation | null = null;
    if (fig && srcRect && !reduced && srcRect.width > 0) {
      const destRect = fig.getBoundingClientRect();
      const scale = srcRect.width / destRect.width;
      const dx = srcRect.left + srcRect.width / 2 - (destRect.left + destRect.width / 2);
      const dy = srcRect.top + srcRect.height / 2 - (destRect.top + destRect.height / 2);
      const arc = Math.min(90, Math.abs(dy) * 0.25 + 30);

      onLift(true);
      anim = fig.animate(
        [
          {
            transform: `translate(${dx}px, ${dy}px) scale(${scale})`,
          },
          {
            transform: `translate(${dx * 0.4}px, ${
              dy * 0.4 - arc
            }px) scale(${((scale + 1) / 2) * 1.03}) rotate(${dx > 0 ? -2.5 : 2.5}deg)`,
            offset: 0.5,
          },
          { transform: "none" },
        ],
        {
          duration: 680,
          easing: "cubic-bezier(.22,.85,.3,1)",
        }
      );
    } else {
      onLift(true);
    }

    const rafId = requestAnimationFrame(() => setMounted(true));
    const rot = rotRef.current;

    return () => {
      cancelAnimationFrame(rafId);
      anim?.cancel();
      document.body.style.overflow = prevOverflow;
      cancelAnimationFrame(rot.raf);
      rot.raf = 0;
      onLift(false);
    };
  }, [source, reduced, onLift]);

  const requestClose = useCallback(() => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;
    setMounted(false);

    const fig = figureRef.current;
    const srcRect = source();
    if (!fig || !srcRect || reduced || srcRect.width === 0) {
      onClose();
      return;
    }

    const destRect = fig.getBoundingClientRect();
    const scale = srcRect.width / destRect.width;
    const dx = srcRect.left + srcRect.width / 2 - (destRect.left + destRect.width / 2);
    const dy = srcRect.top + srcRect.height / 2 - (destRect.top + destRect.height / 2);

    const anim = fig.animate(
      [
        { transform: "none" },
        {
          transform: `translate(${dx * 0.6}px, ${dy * 0.6 - 30}px) scale(${
            (scale + 1) / 2
          })`,
          offset: 0.55,
        },
        { transform: `translate(${dx}px, ${dy}px) scale(${scale})` },
      ],
      {
        duration: 560,
        easing: "cubic-bezier(.45,0,.55,1)",
        fill: "forwards",
      }
    );
    anim.onfinish = () => onClose();
  }, [source, reduced, onClose]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      requestClose();
      return;
    }
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      flipTo(face === "front" ? "back" : "front");
      return;
    }
    if (e.key !== "Tab") return;

    const dialog = dialogRef.current;
    const focusable = [
      ...(dialog?.querySelectorAll<HTMLButtonElement>("button") ?? []),
    ].filter((b) => !b.disabled);
    const first = focusable[0];
    const last = focusable.at(-1);

    if (!first || !last) return;
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  const modalW = shape.w * detailUnit;
  const modalH = shape.h * detailUnit;
  const artistText = [item.artist, item.year].filter(Boolean).join(", ");

  return createPortal(
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-6 text-foreground"
      onKeyDown={onKeyDown}
    >
      <div
        aria-hidden="true"
        className={`absolute inset-0 bg-background/90 backdrop-blur-xl transition-opacity duration-300 motion-reduce:transition-none ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
        onClick={requestClose}
      />

      <button
        ref={closeBtnRef}
        type="button"
        onClick={requestClose}
        className={`absolute right-5 top-5 z-10 inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium tracking-wide text-muted-foreground outline-none transition-[opacity,color] duration-300 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
      >
        {labels.close ?? "Close"}
        <svg
          aria-hidden="true"
          viewBox="0 0 16 16"
          className="h-3.5 w-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        >
          <path d="M3 3l10 10M13 3L3 13" />
        </svg>
      </button>

      <div className="relative grid w-full max-w-5xl items-center justify-items-center gap-8 pt-12 md:grid-cols-[minmax(0,1fr)_minmax(0,20rem)] md:gap-12">
        <div
          ref={figureRef}
          data-figure
          className="relative"
          style={{ width: modalW, height: modalH }}
        >
          <div
            aria-hidden="true"
            className="absolute inset-x-[10%] -bottom-[7%] h-[16%] rounded-[50%] bg-black opacity-[0.18] blur-xl dark:opacity-60"
          />

          <div
            data-spin-area
            className="absolute inset-0 cursor-grab touch-pan-y active:cursor-grabbing"
            style={{ perspective: "1600px" }}
            onPointerDown={(e) => {
              const rot = rotRef.current;
              rot.dragging = true;
              rot.startX = e.clientX;
              rot.startAngle = rot.value;
              cancelAnimationFrame(rot.raf);
              rot.raf = 0;
              rot.last = 0;
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerMove={(e) => {
              const rot = rotRef.current;
              if (rot.dragging) {
                rot.value = clamp(
                  rot.startAngle + (e.clientX - rot.startX) * 0.45,
                  rot.startAngle - 220,
                  rot.startAngle + 220
                );
                if (cardRef.current) {
                  cardRef.current.style.transform = `rotateY(${rot.value.toFixed(2)}deg)`;
                }
              }
            }}
            onPointerUp={() => {
              const rot = rotRef.current;
              if (!rot.dragging) return;
              rot.dragging = false;
              const angleNorm = ((rot.value % 360) + 360) % 360;
              flipTo(angleNorm > 90 && angleNorm < 270 ? "back" : "front");
            }}
            onPointerCancel={() => {
              rotRef.current.dragging = false;
              flipTo(face);
            }}
          >
            <div
              ref={cardRef}
              className="absolute inset-0 [transform-style:preserve-3d]"
            >
              <div
                data-face="front"
                className="absolute inset-0 [backface-visibility:hidden]"
              >
                <FrameArt item={item} shape={shape} unit={detailUnit} lit={0.85} />
              </div>

              <div
                data-face="back"
                className="absolute inset-0 [backface-visibility:hidden]"
                style={{ transform: "rotateY(180deg)" }}
              >
                <FrameBack item={item} shape={shape} unit={detailUnit} />
              </div>
            </div>
          </div>
        </div>

        <div className="flex w-full max-w-sm flex-col gap-4 text-center md:text-left">
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted-foreground">
            {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
          </p>

          <h3 id={titleId} className="text-2xl font-medium tracking-tight sm:text-3xl">
            {item.title}
          </h3>

          {artistText && (
            <p className="text-sm text-muted-foreground">{artistText}</p>
          )}

          {item.tag && (
            <p className="text-lg font-medium tabular-nums">{item.tag}</p>
          )}

          {item.details && item.details.length > 0 && (
            <ul className="flex flex-wrap justify-center gap-2 md:justify-start">
              {item.details.map((dt) => (
                <li
                  key={dt}
                  className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground"
                >
                  {dt}
                </li>
              ))}
            </ul>
          )}

          <div
            role="group"
            aria-label={`${labels.front ?? "Front"} / ${labels.back ?? "Back"}`}
            className="mt-1 inline-flex justify-center gap-6 md:justify-start"
          >
            {(["front", "back"] as const).map((side) => (
              <button
                key={side}
                type="button"
                aria-pressed={face === side}
                onClick={() => flipTo(side)}
                className={`relative rounded-[3px] pb-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-4 focus-visible:ring-offset-background motion-reduce:transition-none ${
                  face === side
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {side === "front"
                  ? labels.front ?? "Front"
                  : labels.back ?? "Back"}
                <span
                  aria-hidden="true"
                  className={`absolute inset-x-0 bottom-0 h-px origin-left bg-foreground transition-transform duration-300 motion-reduce:transition-none ${
                    face === side ? "scale-x-100" : "scale-x-0"
                  }`}
                />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
