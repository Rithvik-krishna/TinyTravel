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
import { TagItem } from "@/lib/tags";
import { inr, shortTime } from "@/lib/format";
import { Lock, AlertTriangle, CheckCircle2 } from "lucide-react";

export interface KeyTagRailProps extends React.HTMLAttributes<HTMLElement> {
  items: TagItem[];
  eyebrow?: string;
  heading?: string;
  caption?: string;
  action?: React.ReactNode;
  autoplay?: boolean;
  interval?: number;
  maxUnit?: number;
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
  open: "Lift to inspect",
};

const PERSPECTIVE = 1200;
const GAP_FACTOR = 0.28;
const EXTRA_ACTIVE_GAP = 0.12;
const CONTACT_EPSILON = 0.05;
const RAIL_PAD = 36;
const MIN_DESKTOP_UNIT = 110;
const DEFAULT_MAX_UNIT = 280; // Large desktop tags (~220px wide)
const MAX_CAROUSEL_UNIT = 190;
const LIFT_SCALE = 0.05;
const SUPERSAMPLE = 2;
const ACTIVE_EXPAND = 1.08;
const LIFT_Z = 24;
const TILT_X = -5;
const AIM_MAX_DEG = 4;
const SWING_MAX_DEG = 12;
const PENDULUM_DAMPING = 2.4;
const GRAVITY_CONST = 3800;
const DRAG_SWING_GAIN = 0.08;
const FREE_SWING_GAIN = 0.16;
const IMPULSE_FORCE = 10;
const DEG_TO_RAD = 180 / Math.PI;

const BRASS_GRADIENT_HOOK =
  "linear-gradient(to bottom, color-mix(in oklab, #facc15 50%, white) 0%, color-mix(in oklab, #ca8a04 80%, white) 30%, color-mix(in oklab, #854d0e 85%, black) 70%, color-mix(in oklab, #713f12 60%, black) 100%)";
const BRASS_GRADIENT_STEM =
  "linear-gradient(to right, color-mix(in oklab, #facc15 70%, white), color-mix(in oklab, #a16207 80%, black) 70%, color-mix(in oklab, #713f12 50%, black))";

function stamp(e: React.PointerEvent | PointerEvent | Event): number {
  const now = performance.now();
  return e.timeStamp > 0 && e.timeStamp <= now + 1 ? e.timeStamp : now;
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}

function restTilt(index: number): number {
  return (((index * 37 + 11) % 7) - 3) * 0.4;
}

interface TagShape {
  aspect: number;
  w: number;
  h: number;
}

function shapeOf(item: TagItem): TagShape {
  const aspect = clamp(item.aspect ?? 0.62, 0.5, 0.75);
  const rootAspect = Math.sqrt(aspect);
  return {
    aspect,
    w: rootAspect,
    h: 1 / rootAspect,
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
  shapes: TagShape[],
  drops: number[],
  width: number,
  maxUnit: number = DEFAULT_MAX_UNIT
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
    : maxUnit;

  // On narrow viewports or when unit falls below threshold, use carousel
  const isNarrow = width < 680;
  const carousel = isNarrow || calculatedUnit < MIN_DESKTOP_UNIT;
  const unit = carousel
    ? clamp(width * 0.44, 140, MAX_CAROUSEL_UNIT)
    : Math.min(maxUnit, calculatedUnit);

  const railTop = 10;
  const railT = Math.round(clamp(unit * 0.08, 12, 20));
  const pivotY = railTop + railT + Math.round(unit * 0.035) + 3;

  const maxH = shapes.reduce((max, s) => Math.max(max, s.h), 0) * unit;
  const midY = pivotY + unit * 0.18 + maxH / 2;

  const tops = shapes.map((s, i) =>
    Math.round(
      Math.max(
        pivotY + unit * 0.08,
        midY - (s.h * unit) / 2 + clamp(drops[i] ?? 0, 0, 0.3) * unit
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
    stageH: Math.round(maxBottom + 44),
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

function pendulum(layout: RailLayout, shape: TagShape, index: number): number {
  return Math.max(
    40,
    (layout.tops[index] ?? 0) - layout.pivotY + (shape.h * layout.unit) / 2
  );
}

function reach(
  sim: Sim,
  layout: RailLayout,
  shape: TagShape,
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
  shapes: TagShape[],
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

export function KeyTagRail({
  items,
  eyebrow,
  heading,
  caption,
  action,
  autoplay = false,
  interval = 3200,
  maxUnit = DEFAULT_MAX_UNIT,
  active: controlledActive,
  onActiveChange,
  onOpenChange,
  labels = DEFAULT_LABELS,
  className,
  ...props
}: KeyTagRailProps) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const count = items.length;
  const isControlled = controlledActive !== undefined;

  const stageRef = useRef<HTMLDivElement>(null);
  const hangRefs = useRef<(HTMLDivElement | null)[]>([]);
  const shadowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const swingRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const tiltRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const shadowInnerRefs = useRef<(HTMLSpanElement | null)[]>([]);

  const simRef = useRef<Sim>(emptySim());
  const shapes = useMemo(() => items.map(shapeOf), [items]);
  const drops = useMemo(() => items.map((it) => it.drop ?? 0), [items]);

  const [containerWidth, setContainerWidth] = useState(0);
  const layout = useMemo(
    () => layoutFor(shapes, drops, containerWidth, maxUnit),
    [shapes, drops, containerWidth, maxUnit]
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
    const { layout: l, shapes: sh } = stateRef.current;
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

    const shadowInner = shadowInnerRefs.current[i];
    if (shadowInner) {
      shadowInner.style.transform = `translate3d(${(-tiltDeg * 1.4).toFixed(
        2
      )}px,${(l.unit * 0.04 + 10 * liftNorm).toFixed(2)}px,0) scale(${(
        1 +
        0.035 * liftNorm
      ).toFixed(4)},${(1 + 0.07 * liftNorm).toFixed(4)})`;
      shadowInner.style.opacity = (1 - 0.25 * liftActive).toFixed(3);
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
          () => impulse(i, 14 - i * 1.5),
          140 + i * 80
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
      autoplayNextTime.current = now + (activeIndex === null ? 1200 : interval);
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
      impulse(idx, idx % 2 ? 18 : -18);
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
  const unitPx = layout.unit;
  const shadowBlur = Math.max(3, unitPx * 0.05);

  return (
    <section
      {...props}
      data-slot="key-tag-rail"
      data-mode={layout.carousel ? "carousel" : "rail"}
      data-active={activeIndex ?? ""}
      aria-roledescription="key tag rail"
      className={`relative isolate w-full overflow-hidden text-text ${
        className ?? ""
      }`}
    >
      {(eyebrow || heading) && (
        <header className="relative z-10 flex flex-col items-center gap-3 px-6 pt-4 text-center">
          {eyebrow && (
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-brand">
              {eyebrow}
            </p>
          )}
          {heading && (
            <h2 className="text-balance text-4xl sm:text-6xl font-extrabold tracking-tight max-w-4xl text-text">
              {heading}
            </h2>
          )}
          {caption && (
            <p className="max-w-2xl text-base sm:text-lg text-text-muted mt-1 leading-relaxed">
              {caption}
            </p>
          )}
          {action && <div className="mt-3 flex items-center gap-4">{action}</div>}
        </header>
      )}

      <div
        ref={stageRef}
        data-stage
        role="group"
        aria-label={heading ?? "Key tag rail"}
        className="relative mt-2 w-full touch-pan-y select-none"
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
          if (!document.activeElement?.matches("[data-tag]:focus-visible")) {
            setActive(null);
          }
          kick();
        }}
        onKeyDown={onKeyDown}
      >
        {/* Solid Brass Hanging Rail */}
        <div
          aria-hidden="true"
          data-rail
          className="pointer-events-none absolute inset-x-0 z-[1]"
          style={{ top: layout.railTop, height: layout.railT }}
        >
          {/* Subtle warm rail cast shadow */}
          <div className="absolute inset-x-0 top-full h-4 bg-black/15 blur-[6px] dark:bg-black/50" />

          {/* Brass extrusion bar */}
          <div
            className="absolute inset-0 rounded-[2px]"
            style={{
              background:
                "linear-gradient(to bottom, #fef08a 0%, #eab308 14%, #ca8a04 36%, #a16207 58%, #713f12 82%, #451a03 100%)",
              boxShadow:
                "0 3px 6px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.8), inset 0 -1px 0 rgba(0,0,0,0.45)",
            }}
          />
          {/* Polished brass highlight reflection */}
          <div className="absolute inset-x-0 top-[22%] h-[1.5px] bg-white/75" />
          <div className="absolute inset-x-0 bottom-0 h-px bg-black/40" />
        </div>

        {/* Dynamic drop shadows beneath swinging tags */}
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
                  className="absolute opacity-25 dark:opacity-65"
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
                    className="absolute inset-0 rounded-2xl bg-black"
                  />
                </span>
              </div>
            );
          })}
        </div>

        {/* Hanging key tags */}
        {items.map((item, i) => {
          const sh = shapes[i];
          if (!sh) return null;
          const fw = sh.w * unitPx;
          const fh = sh.h * unitPx;
          const topY = layout.tops[i] ?? 0;
          const isAct = activeIndex === i;
          // String connects to brass eyelet hole near tag top
          const eyeletOffsetY = Math.round(fw * 0.12);
          const stringTargetY = topY + eyeletOffsetY;

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
              {/* Solid brass sliding collar */}
              <RailRingHook
                x={fw / 2}
                railTop={layout.railTop}
                railT={layout.railT}
                pivotY={layout.pivotY}
              />

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
                {/* Woven braided cord hanging from rail hook down into eyelet */}
                <svg
                  aria-hidden="true"
                  className="pointer-events-none absolute left-0 top-0 overflow-visible"
                  width={Math.max(1, fw)}
                  height={Math.max(1, stringTargetY)}
                >
                  {/* Cord drop shadow */}
                  <line
                    x1={fw / 2 + 1}
                    y1={layout.pivotY + 2}
                    x2={fw / 2 + 1}
                    y2={stringTargetY + 1}
                    stroke="black"
                    strokeOpacity="0.2"
                    strokeWidth="2.6"
                  />
                  {/* Twined cord threads */}
                  <line
                    x1={fw / 2 - 0.7}
                    y1={layout.pivotY}
                    x2={fw / 2 - 0.7}
                    y2={stringTargetY}
                    stroke="#b45309"
                    strokeWidth="1.8"
                    strokeDasharray="4 2"
                  />
                  <line
                    x1={fw / 2 + 0.7}
                    y1={layout.pivotY}
                    x2={fw / 2 + 0.7}
                    y2={stringTargetY}
                    stroke="#d97706"
                    strokeWidth="1.8"
                    strokeDasharray="2 4"
                  />
                  <line
                    x1={fw / 2}
                    y1={layout.pivotY}
                    x2={fw / 2}
                    y2={stringTargetY}
                    stroke="#fef3c7"
                    strokeOpacity="0.5"
                    strokeWidth="0.9"
                  />
                </svg>

                <button
                  ref={(el) => {
                    buttonRefs.current[i] = el;
                  }}
                  type="button"
                  data-tag={i}
                  data-lit={isAct || undefined}
                  tabIndex={i === (activeIndex ?? focusIndex) ? 0 : -1}
                  aria-label={`${item.title} on ${item.platform} - Listing price ${inr(
                    item.listing
                  )} - Click or tap to flip`}
                  aria-describedby={`${uid}-caption`}
                  aria-pressed={isAct}
                  className="pointer-events-auto absolute cursor-pointer rounded-2xl outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-brand"
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
                      <TagFront item={item} shape={sh} unit={unitPx} />
                    </span>
                  </span>
                </button>
              </span>
            </div>
          );
        })}
      </div>

      {/* Mobile carousel indicator pills */}
      {layout.carousel && count > 1 && (
        <div
          className="relative z-10 mt-3 flex justify-center gap-1.5"
          role="group"
          aria-label={heading ?? "Tags"}
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
              className={`h-1.5 rounded-full outline-none transition-[width,background-color] duration-300 focus-visible:ring-2 focus-visible:ring-brand motion-reduce:transition-none ${
                carouselIndicatorActive === i
                  ? "w-6 bg-brand"
                  : "w-1.5 bg-text-muted/30 hover:bg-text-muted/60"
              }`}
            />
          ))}
        </div>
      )}

      {/* Detail Modal with 3D Flip */}
      {openIndex !== null && items[openIndex] && shapes[openIndex] && (
        <TagDetailModal
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

/**
 * RailRingHook: Sturdy brass hardware collar that rides on top rail
 */
function RailRingHook({
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
  const ringRadius = clamp(railT * 0.42, 5, 9);
  const hookH = pivotY - railTop + 8;
  return (
    <span
      aria-hidden="true"
      className="absolute"
      style={{
        left: x - ringRadius,
        top: railTop - 3,
        width: ringRadius * 2,
        height: hookH,
      }}
    >
      {/* Top brass loop collar over rail */}
      <span
        className="absolute inset-x-0 top-0 rounded-full"
        style={{
          height: 6,
          background: BRASS_GRADIENT_HOOK,
          boxShadow: "0 1px 3px rgba(0,0,0,0.35)",
        }}
      />
      {/* Vertical brass drop tab */}
      <span
        className="absolute top-[4px] rounded-b-[1px]"
        style={{
          left: ringRadius * 0.5,
          width: ringRadius,
          bottom: 6,
          background: BRASS_GRADIENT_STEM,
          boxShadow: "1px 1px 2px rgba(0,0,0,0.25)",
        }}
      />
      {/* Eyelet ring hole at bottom of hook */}
      <svg
        aria-hidden="true"
        className="absolute bottom-0 left-0 overflow-visible"
        width={ringRadius * 2}
        height={10}
      >
        <circle
          cx={ringRadius}
          cy={5}
          r={ringRadius * 0.82}
          fill="none"
          stroke="#ca8a04"
          strokeWidth="2.2"
        />
        <circle cx={ringRadius} cy={5} r={ringRadius * 0.4} fill="#451a03" />
      </svg>
    </span>
  );
}

/**
 * TagFront: Redesigned unit-scaled physical key tag
 */
export function TagFront({
  item,
  shape,
  unit,
}: {
  item: TagItem;
  shape: TagShape;
  unit: number;
}) {
  const eyeletSize = Math.max(16, Math.round(unit * 0.11));
  const eyeletCenterY = Math.max(14, Math.round(unit * 0.1));
  const platformLabel = item.platform;

  const isVerified = item.status === "verified";
  const isBlocked = item.status === "blocked";
  const isUnverified = item.status === "unverified";
  const isNonRefundable = item.cancellation_category === "non_refundable";

  const cardBorderClass = isUnverified
    ? "border-2 border-dashed border-warning/70 bg-surface/90"
    : isBlocked
    ? "border-2 border-danger/40 bg-surface/90"
    : "border border-border/80 bg-surface-2";

  return (
    <div className={`relative h-full w-full select-none rounded-2xl ${cardBorderClass} shadow-[0_10px_30px_rgba(0,0,0,0.08),0_2px_4px_rgba(0,0,0,0.04)] dark:shadow-[0_12px_36px_rgba(0,0,0,0.55)] overflow-hidden flex flex-col justify-between p-3.5 sm:p-5 transition-colors`}>
      {/* Subtle hotel cardstock texture & inner border bevel */}
      <div className="pointer-events-none absolute inset-1.5 sm:inset-2 rounded-[14px] border border-border/40" />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/15 via-transparent to-black/5 dark:from-white/5 dark:to-black/30" />

      {/* Top area: Punched Brass Eyelet */}
      <div
        className="relative z-10 flex flex-col items-center flex-shrink-0"
        style={{ marginTop: Math.max(0, eyeletCenterY - 14) }}
      >
        <div
          className="relative rounded-full flex items-center justify-center"
          style={{
            width: eyeletSize,
            height: eyeletSize,
            background:
              "radial-gradient(circle, #fef08a 0%, #eab308 35%, #ca8a04 65%, #713f12 100%)",
            boxShadow:
              "0 1.5px 3px rgba(0,0,0,0.4), inset 0 1px 1px rgba(255,255,255,0.9), inset 0 -1px 1px rgba(0,0,0,0.6)",
          }}
        >
          {/* Eyelet hole cutout */}
          <div
            className="rounded-full bg-surface"
            style={{
              width: Math.round(eyeletSize * 0.44),
              height: Math.round(eyeletSize * 0.44),
              boxShadow: "inset 0 1.5px 3px rgba(0,0,0,0.7)",
            }}
          />
        </div>

        {/* Stage 2 Stamp / Badge */}
        <div className="mt-2 text-center">
          {isVerified && item.verifiedAt ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-success/15 border border-success/40 text-success font-bold uppercase tracking-wider px-2 py-0.5"
              style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
            >
              ✓ Verified {shortTime(item.verifiedAt)}
            </span>
          ) : isBlocked ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-danger/15 border border-danger/40 text-danger font-bold uppercase tracking-wider px-2 py-0.5"
              style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
            >
              <Lock className="w-3 h-3 inline" /> Stopped at {item.blocker || "captcha"}
            </span>
          ) : isUnverified ? (
            <span
              className="inline-flex items-center gap-1 rounded bg-warning/15 border border-warning/40 text-warning font-bold uppercase tracking-wider px-2 py-0.5"
              style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
            >
              <AlertTriangle className="w-3 h-3 inline" /> NOT VERIFIED
            </span>
          ) : null}
        </div>
      </div>

      {/* Mid area: Platform badge & Hotel Name (up to 2 lines, no ellipsis) */}
      <div className="relative z-10 my-auto text-center space-y-2 px-1 flex-1 flex flex-col justify-center">
        <div>
          <span
            className="inline-flex items-center rounded-full bg-surface border border-border/90 px-3 py-1 font-medium text-text-muted shadow-sm max-w-full"
            style={{ fontSize: `${clamp(Math.round(unit * 0.046), 11, 14)}px` }}
          >
            {platformLabel}
          </span>
        </div>

        <h3
          className="font-bold text-text leading-tight tracking-tight break-words"
          style={{ fontSize: `${clamp(Math.round(unit * 0.076), 14, 21)}px` }}
        >
          {item.title}
        </h3>

        {/* Non-refundable warning chip */}
        {isNonRefundable && (
          <div className="pt-0.5">
            <span
              className="inline-block rounded bg-warning/10 border border-warning/30 text-warning font-semibold leading-tight px-1.5 py-0.5"
              style={{ fontSize: `${clamp(Math.round(unit * 0.036), 8, 10)}px` }}
            >
              Non-refundable, not comparable with free cancellation
            </span>
          </div>
        )}
      </div>

      {/* Bottom area: Separated Price Block with Label ABOVE Amount */}
      <div className="relative z-10 text-center pt-2.5 pb-1 border-t border-border/70 flex-shrink-0 space-y-1">
        <div
          className="font-semibold uppercase tracking-wider text-text-muted"
          style={{ fontSize: `${clamp(Math.round(unit * 0.042), 9, 12)}px` }}
        >
          Listing price
        </div>
        <div
          className="font-extrabold text-text tabular-nums tracking-tight leading-none"
          style={{ fontSize: `${clamp(Math.round(unit * 0.125), 18, 34)}px` }}
        >
          {inr(item.listing)}
        </div>
        <div
          className="text-brand font-medium pt-1 opacity-90"
          style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
        >
          Tap to flip ↺
        </div>
      </div>
    </div>
  );
}

/**
 * TagBack: Flipped receipt / real payable price side
 */
export function TagBack({
  item,
  shape,
  unit,
}: {
  item: TagItem;
  shape: TagShape;
  unit: number;
}) {
  const eyeletSize = Math.max(16, Math.round(unit * 0.11));
  const eyeletCenterY = Math.max(14, Math.round(unit * 0.1));

  const hasPayable = typeof item.payable === "number";
  const delta = hasPayable && typeof item.listing === "number" ? item.payable! - item.listing! : null;
  const deltaSign = delta !== null && delta >= 0 ? "+" : "";
  const deltaPct = item.fee_leak_pct != null ? ` (+${item.fee_leak_pct}%)` : "";
  const verifiedStr = item.verifiedAt ? `Verified at ${shortTime(item.verifiedAt)}` : "Observed on this run";

  return (
    <div className="relative h-full w-full select-none rounded-2xl bg-surface border border-border/80 shadow-[0_10px_30px_rgba(0,0,0,0.1)] dark:shadow-[0_12px_36px_rgba(0,0,0,0.6)] overflow-hidden flex flex-col justify-between p-3.5 sm:p-5">
      {/* Punched Eyelet on Back */}
      <div
        className="relative z-10 flex flex-col items-center flex-shrink-0"
        style={{ marginTop: Math.max(0, eyeletCenterY - 14) }}
      >
        <div
          className="rounded-full flex items-center justify-center"
          style={{
            width: eyeletSize,
            height: eyeletSize,
            background:
              "radial-gradient(circle, #eab308 0%, #ca8a04 50%, #713f12 100%)",
            boxShadow: "0 1.5px 3px rgba(0,0,0,0.35)",
          }}
        >
          <div
            className="rounded-full bg-surface-2"
            style={{
              width: Math.round(eyeletSize * 0.44),
              height: Math.round(eyeletSize * 0.44),
            }}
          />
        </div>
      </div>

      {/* Back Body: Big Real Payable Price */}
      <div className="relative z-10 my-auto text-center space-y-2.5 px-1 flex-1 flex flex-col justify-center">
        <p
          className="font-medium text-text-muted"
          style={{ fontSize: `${clamp(Math.round(unit * 0.046), 11, 14)}px` }}
        >
          {item.platform}
        </p>

        {item.status === "verified" && hasPayable ? (
          <div className="space-y-1">
            <div
              className="font-semibold uppercase tracking-wider text-text-muted"
              style={{ fontSize: `${clamp(Math.round(unit * 0.042), 9, 12)}px` }}
            >
              You&apos;d pay
            </div>
            <div
              className="font-extrabold text-text tabular-nums tracking-tight leading-none text-danger"
              style={{ fontSize: `${clamp(Math.round(unit * 0.125), 18, 34)}px` }}
            >
              {inr(item.payable)}
            </div>
          </div>
        ) : item.status === "blocked" ? (
          <div className="space-y-1">
            <div className="flex items-center justify-center gap-1 font-bold text-danger text-xs sm:text-sm">
              <Lock className="w-3.5 h-3.5 inline" />
              <span>Stopped at {item.blocker || "captcha"}</span>
            </div>
            <div className="font-extrabold text-text text-2xl">
              N/A
            </div>
            <p className="text-[10px] text-text-muted">
              Anti-bot challenge stopped probe
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            <div
              className="font-semibold uppercase tracking-wider text-warning text-xs sm:text-sm"
              style={{ fontSize: `${clamp(Math.round(unit * 0.042), 9, 12)}px` }}
            >
              NOT VERIFIED
            </div>
            <div className="font-extrabold text-text text-2xl">
              N/A
            </div>
            <p className="text-[10px] text-text-muted">
              Checkout funnel not completed
            </p>
          </div>
        )}

        {/* Delta Chip */}
        {delta !== null ? (
          <div className="pt-1">
            <span
              className="inline-block rounded-lg bg-danger/10 border border-danger/30 text-danger px-2.5 py-1 font-semibold leading-tight"
              style={{ fontSize: `${clamp(Math.round(unit * 0.04), 9, 12)}px` }}
            >
              {deltaSign}{inr(delta)}{deltaPct} observed on this run
            </span>
          </div>
        ) : item.blocker ? (
          <div className="pt-1">
            <span
              className="inline-block rounded-lg bg-warning/10 border border-warning/30 text-warning px-2.5 py-1 font-semibold leading-tight"
              style={{ fontSize: `${clamp(Math.round(unit * 0.04), 9, 12)}px` }}
            >
              Stopped at {item.blocker}
            </span>
          </div>
        ) : null}
      </div>

      {/* Bottom Area: Timestamp & Flip back */}
      <div className="relative z-10 text-center pt-2.5 pb-1 border-t border-border/70 flex-shrink-0 space-y-1">
        <div
          className="text-text-muted font-medium"
          style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
        >
          {verifiedStr}
        </div>
        <div
          className="text-brand font-medium"
          style={{ fontSize: `${clamp(Math.round(unit * 0.038), 9, 11)}px` }}
        >
          Flip to front ↻
        </div>
      </div>
    </div>
  );
}

function fitDetailUnit(shape: TagShape): number {
  if (typeof window === "undefined") return 300;
  const isMd = window.innerWidth >= 768;
  const maxW = isMd
    ? Math.min(520, window.innerWidth * 0.44)
    : window.innerWidth * 0.78;
  const maxH = isMd
    ? Math.min(520, window.innerHeight * 0.65)
    : window.innerHeight * 0.46;
  return Math.max(90, Math.min(maxW / shape.w, maxH / shape.h));
}

/**
 * TagDetailModal: 3D modal with front/back flip
 */
function TagDetailModal({
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
  item: TagItem;
  shape: TagShape;
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
  const [detailUnit, setDetailUnit] = useState(() => fitDetailUnit(shape));

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
    const handleResize = () => setDetailUnit(fitDetailUnit(shape));
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

  return createPortal(
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto p-6 text-text"
      onKeyDown={onKeyDown}
    >
      <div
        aria-hidden="true"
        className={`absolute inset-0 bg-black/60 backdrop-blur-xl transition-opacity duration-300 motion-reduce:transition-none ${
          mounted ? "opacity-100" : "opacity-0"
        }`}
        onClick={requestClose}
      />

      <button
        ref={closeBtnRef}
        type="button"
        onClick={requestClose}
        className={`absolute right-5 top-5 z-10 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-text-muted shadow-sm outline-none transition-[opacity,color] duration-300 hover:text-text focus-visible:ring-2 focus-visible:ring-brand motion-reduce:transition-none ${
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

      <div className="relative grid w-full max-w-4xl items-center justify-items-center gap-8 pt-12 md:grid-cols-[minmax(0,1fr)_minmax(0,18rem)] md:gap-12">
        <div
          ref={figureRef}
          data-figure
          className="relative"
          style={{ width: modalW, height: modalH }}
        >
          <div
            aria-hidden="true"
            className="absolute inset-x-[10%] -bottom-[8%] h-[18%] rounded-[50%] bg-black opacity-20 blur-xl dark:opacity-60"
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
                <TagFront item={item} shape={shape} unit={detailUnit} />
              </div>

              <div
                data-face="back"
                className="absolute inset-0 [backface-visibility:hidden]"
                style={{ transform: "rotateY(180deg)" }}
              >
                <TagBack item={item} shape={shape} unit={detailUnit} />
              </div>
            </div>
          </div>
        </div>

        <div className="flex w-full max-w-sm flex-col gap-4 text-center md:text-left">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-text-muted">
            Offer {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
          </p>

          <h3 id={titleId} className="text-2xl font-bold tracking-tight sm:text-3xl text-text">
            {item.title}
          </h3>

          <p className="text-sm font-semibold text-brand">
            {item.platform}
          </p>

          <div className="space-y-2 rounded-xl bg-surface-2 border border-border p-4 text-left">
            <div className="flex justify-between items-baseline">
              <span className="text-xs text-text-muted">Listing price:</span>
              <span className="text-lg font-bold text-text tabular-nums">
                {inr(item.listing)}
              </span>
            </div>
            {typeof item.payable === "number" && (
              <div className="flex justify-between items-baseline pt-2 border-t border-border/60">
                <span className="text-xs font-semibold text-danger">Real payable:</span>
                <span className="text-xl font-extrabold text-danger tabular-nums">
                  {inr(item.payable)}
                </span>
              </div>
            )}
          </div>

          <div
            role="group"
            aria-label={`${labels.front ?? "Front"} / ${labels.back ?? "Back"}`}
            className="mt-2 inline-flex justify-center gap-6 md:justify-start"
          >
            {(["front", "back"] as const).map((side) => (
              <button
                key={side}
                type="button"
                aria-pressed={face === side}
                onClick={() => flipTo(side)}
                className={`relative rounded-[3px] pb-1.5 text-sm font-semibold outline-none transition-colors focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-4 focus-visible:ring-offset-surface motion-reduce:transition-none ${
                  face === side
                    ? "text-text"
                    : "text-text-muted hover:text-text"
                }`}
              >
                {side === "front"
                  ? labels.front ?? "Front"
                  : labels.back ?? "Back"}
                <span
                  aria-hidden="true"
                  className={`absolute inset-x-0 bottom-0 h-0.5 origin-left bg-brand transition-transform duration-300 motion-reduce:transition-none ${
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

export default KeyTagRail;
