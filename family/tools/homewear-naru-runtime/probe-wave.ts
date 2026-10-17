/** Consumer physics proof for all remaining Family homewear outfits using public rig-c/core and the installed official oracle. */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { readModel, underNoSkin, openTrack, physicsClockStep } from 'rig-c/core';
import { createWindControls } from '../../viewer/wind-controls.mjs';
import { loadPosable, piecesOf, renderFrame } from 'rig-c/render';
import { Skeleton, AnimationState, AnimationStateData, Physics, MeshAttachment, RegionAttachment } from '@esotericsoftware/spine-core';

type Pose = ReturnType<typeof openTrack>['first'];
type Flat = { bones: [string, number[]][]; drawn: [string, string, number[]][] };
type Scenario = 'calm' | 'wind4' | 'gust' | 'drag' | 'burst48' | 'burst96';

const family = resolve(import.meta.dir, '../..');
const args = process.argv.slice(2);
function option(name: string, fallback: string) {
  const at = args.indexOf('--' + name);
  return at < 0 ? fallback : (args[at + 1] ?? fallback);
}
const charsArg = option('characters', 'roa,luna,jinni,nova').split(',').filter(Boolean);
const outfitArg = option('outfit', 'homewear');
const doRender = !args.includes('--no-render');
const json = (p: string) => JSON.parse(readFileSync(p, 'utf8'));

const flatten = (p: Pose): Flat => ({
  bones: p.bones.map(b => [b.name, [b.a, b.b, b.c, b.d, b.worldX, b.worldY]]),
  drawn: p.drawn.map(d => [d.slot, d.attachment, d.vertices]),
});

function native(sk: Skeleton): Flat {
  const drawn: Flat['drawn'] = [];
  for (const s of sk.drawOrder.appliedPose) {
    const a = s.appliedPose.attachment;
    if (!(a instanceof MeshAttachment) && !(a instanceof RegionAttachment)) continue;
    const v = new Array<number>(a instanceof MeshAttachment ? a.worldVerticesLength : 8).fill(0);
    if (a instanceof MeshAttachment) a.computeWorldVertices(sk, s, 0, v.length, v, 0, 2);
    else a.computeWorldVertices(s, a.getOffsets(s.appliedPose), v, 0, 2);
    drawn.push([s.data.name, a.name, v]);
  }
  return {
    bones: sk.bones.map(b => [
      b.data.name,
      [b.appliedPose.a, b.appliedPose.b, b.appliedPose.c, b.appliedPose.d, b.appliedPose.worldX, b.appliedPose.worldY],
    ]),
    drawn,
  };
}

function numbers(a: number[], b: number[]) {
  if (a.length !== b.length) throw Error('HOMEWEAR_COORDINATE_LENGTH');
  let d = 0;
  for (let i = 0; i < a.length; i++) {
    if (!Number.isFinite(a[i]) || !Number.isFinite(b[i])) throw Error('HOMEWEAR_NONFINITE');
    d = Math.max(d, Math.abs(a[i] - b[i]));
  }
  return d;
}

function difference(a: Flat, b: Flat) {
  if (a.bones.length !== b.bones.length || a.drawn.length !== b.drawn.length) throw Error('HOMEWEAR_ROW_COUNT');
  let d = 0;
  for (let i = 0; i < a.bones.length; i++) {
    if (a.bones[i][0] !== b.bones[i][0]) throw Error('HOMEWEAR_BONE_NAME');
    d = Math.max(d, numbers(a.bones[i][1], b.bones[i][1]));
  }
  for (let i = 0; i < a.drawn.length; i++) {
    if (a.drawn[i][0] !== b.drawn[i][0]) throw Error('HOMEWEAR_SLOT_NAME');
    d = Math.max(d, numbers(a.drawn[i][2], b.drawn[i][2]));
  }
  return d;
}

function geometry(p: Flat, n: string) {
  const r = p.drawn.find(d => d[0] === n);
  if (!r) throw Error('HOMEWEAR_SLOT_ABSENT ' + n);
  return r[2];
}

function bone(p: Flat, n: string) {
  const b = p.bones.find(b => b[0] === n);
  if (!b) throw Error('HOMEWEAR_BONE_ABSENT ' + n);
  return b[1];
}

function area(v: number[], a: number, b: number, c: number) {
  return (v[2 * b] - v[2 * a]) * (v[2 * c + 1] - v[2 * a + 1]) - (v[2 * b + 1] - v[2 * a + 1]) * (v[2 * c] - v[2 * a]);
}

const fps = 60, frames = 721, selected = new Set([0, 60, 72, 120, 126, 150, 200, 360, 720]);

function probeCharacter(char: string) {
  const home = join(family, 'outfits', outfitArg, char);
  const out = join(home, 'runtime');
  const candidateDirectory = join(home, 'out/check/build');
  const baselineDirectory = join(family, char, 'out/check/build');
  mkdirSync(out, { recursive: true });
  const oldRig = json(join(family, char, 'out/rig/rig.json'));
  const newRig = json(join(home, 'out/rig/rig.json'));
  const commonSlots: string[] = json(join(home, 'out/assembly.json')).commonSlots;
  const newSlots: string[] = json(join(home, 'out/assembly.json')).newClothingSlots;

  function walk(dir: string, scenario: Scenario, kind: string) {
    const doc = underNoSkin(readModel(readFileSync(join(dir, 'skeleton.model.json'), 'utf8'), dir));
    const loaded = loadPosable(join(dir, 'skeleton.json'), join(dir, 'skeleton.atlas'), dir);
    const sk = new Skeleton(loaded.data);
    const state = new AnimationState(new AnimationStateData(loaded.data));
    const track = openTrack(doc, 'idle', { loop: true, reset: 'animation', clock: physicsClockStep });
    state.setAnimation(0, 'idle', true);
    sk.setupPose();
    sk.updateWorldTransform(Physics.none);
    state.apply(sk);
    sk.update(0);
    sk.updateWorldTransform(Physics.reset);
    const result: Flat[] = [flatten(track.first)];
    let delta = difference(result[0], native(sk));
    const controls = createWindControls();
    if (scenario === 'wind4') controls.setBase(4);
    if (scenario === 'gust') controls.setBreeze(true);
    if (scenario === 'burst48' || scenario === 'burst96') {
      controls.setGustPeak(scenario === 'burst48' ? 48 : 96);
      controls.triggerGust();
    }
    function render(i: number) {
      if (!doRender || kind !== 'candidate' || !selected.has(i)) return;
      for (const [view, vp] of Object.entries({
        full: { minX: -400, minY: 0, maxX: 400, maxY: 2284, scale: 0.5, width: 400, height: 1142 },
        neckHands: { minX: -270, minY: 1250, maxX: 270, maxY: 2014, scale: 1, width: 540, height: 764 },
      })) {
        const target = join(out, scenario, view);
        mkdirSync(target, { recursive: true });
        renderFrame({ index: i, time: i / fps, pieces: piecesOf(sk) }, loaded.pages, vp, [32, 38, 48, 255]).writePng(
          join(target, 'f' + String(i).padStart(4, '0') + '.png'),
        );
      }
    }
    render(0);
    for (let i = 1; i < frames; i++) {
      const w = controls.advance(1 / fps).wind;
      track.setEnvironment({ wind: [w, 0], gravity: [0, 0] });
      sk.windX = w;
      sk.windY = sk.gravityX = sk.gravityY = 0;
      if (scenario === 'drag' && (i === 120 || i === 126)) {
        const dx = i === 120 ? 18 : -18, dy = i === 120 ? -10 : 10;
        track.physicsTranslate(dx, dy);
        sk.physicsTranslate(dx, dy);
      }
      state.update(1 / fps);
      sk.setupPoseBones();
      state.apply(sk);
      sk.update(physicsClockStep(1 / fps));
      sk.updateWorldTransform(Physics.update);
      const p = flatten(track.step(1 / fps));
      delta = Math.max(delta, difference(p, native(sk)));
      result.push(p);
      render(i);
    }
    if (delta !== 0) throw Error('HOMEWEAR_NATIVE_CORE_PARITY ' + char + '/' + kind + '/' + scenario + ' ' + delta);
    return { poses: result, nativeCoreMaxDelta: delta };
  }

  const cases: object[] = [];
  const calm = walk(candidateDirectory, 'calm', 'candidate');
  for (const scenario of ['calm', 'wind4', 'gust', 'drag', 'burst48', 'burst96'] as Scenario[]) {
    const candidate = scenario === 'calm' ? calm : walk(candidateDirectory, scenario, 'candidate');
    const baseline = walk(baselineDirectory, scenario, 'baseline');
    let commonBoneMaxDelta = 0, commonAttachmentMaxDelta = 0, bustBoneMaxDelta = 0;
    const response: Record<string, { windOrDragOnlyMax: number; foldingTriangleReadings: number; minEdgeRatio: number; maxEdgeRatio: number }> = {};
    for (const slot of newSlots) response[slot] = { windOrDragOnlyMax: 0, foldingTriangleReadings: 0, minEdgeRatio: Infinity, maxEdgeRatio: 0 };
    for (let i = 0; i < frames; i++) {
      const a = baseline.poses[i], b = candidate.poses[i];
      for (const name of oldRig.bones.map((r: { name: string }) => r.name)) commonBoneMaxDelta = Math.max(commonBoneMaxDelta, numbers(bone(a, name), bone(b, name)));
      for (const name of commonSlots) commonAttachmentMaxDelta = Math.max(commonAttachmentMaxDelta, numbers(geometry(a, name), geometry(b, name)));
      for (const name of ['boob_r', 'boob_l']) bustBoneMaxDelta = Math.max(bustBoneMaxDelta, numbers(bone(a, name), bone(b, name)));
      for (const slot of newSlots) {
        const r = response[slot], v = geometry(b, slot), z = geometry(calm.poses[i], slot), rest = geometry(calm.poses[0], slot);
        for (let p = 0; p < v.length; p += 2) r.windOrDragOnlyMax = Math.max(r.windOrDragOnlyMax, Math.hypot(v[p] - z[p], v[p + 1] - z[p + 1]));
        const at = newRig.skins.default[slot][slot];
        if (!at.triangles) continue;
        for (let q = 0; q < at.triangles.length; q += 3) {
          const tri: number[] = at.triangles.slice(q, q + 3);
          if (area(v, tri[0], tri[1], tri[2]) * area(rest, tri[0], tri[1], tri[2]) <= 0) r.foldingTriangleReadings++;
          for (let e = 0; e < 3; e++) {
            const x = tri[e], y = tri[(e + 1) % 3], base = Math.hypot(rest[x * 2] - rest[y * 2], rest[x * 2 + 1] - rest[y * 2 + 1]);
            if (base > 0) {
              const ratio = Math.hypot(v[x * 2] - v[y * 2], v[x * 2 + 1] - v[y * 2 + 1]) / base;
              r.minEdgeRatio = Math.min(r.minEdgeRatio, ratio);
              r.maxEdgeRatio = Math.max(r.maxEdgeRatio, ratio);
            }
          }
        }
      }
    }
    const PASS =
      commonBoneMaxDelta === 0 &&
      commonAttachmentMaxDelta === 0 &&
      bustBoneMaxDelta === 0 &&
      Object.values(response).every(r => r.foldingTriangleReadings === 0) &&
      (!response.hands || response.hands.windOrDragOnlyMax === 0) &&
      response.sleeves.windOrDragOnlyMax === 0 &&
      response.bottomwear.windOrDragOnlyMax === 0;
    cases.push({ scenario, nativeCoreMaxDelta: 0, commonBoneMaxDelta, commonAttachmentMaxDelta, bustBoneMaxDelta, response, PASS });
    console.log(JSON.stringify({ character: char, ...(cases[cases.length - 1] as object) }));
  }
  const report = {
    spec: `family-${outfitArg}-live-physics/1`,
    character: char,
    contract: {
      fps,
      frames,
      seconds: 12,
      scenarios: ['calm', 'wind4', 'gust', 'drag', 'burst48', 'burst96'],
      windAdapter: 'actual family/viewer/wind-controls.mjs; base4, breeze and burst48/96 with base0, duration2.4s, positive singlepulse',
      drag: 'public physicsTranslate(+18,-10) at2s, (-18,+10) at2.1s; viewer90ms return sampled at60Hz nextframe; no world position teleport',
      physicsClock: 'public physicsClockStep',
      environment: 'wind[y]=0, gravity[0,0]; applied after first/reset pose',
      oracle: 'official Spine4.3.13; exact all posed bone matrices and attachment vertices',
      screenshots: doRender ? 'native oracle rendered on dark background; no browser execution claim' : 'omitted by --no-render; numerical geometry only',
      source: `original common ${oldRig.bones.length} bones + ${commonSlots.length} head/hair attachments compared at every same-phase frame`,
    },
    cases,
    PASS: cases.every(c => (c as { PASS: boolean }).PASS),
  };
  writeFileSync(join(out, 'physics.json'), JSON.stringify(report, null, 2) + '\n');
  if (!report.PASS) throw Error('HOMEWEAR_PHYSICS_FAILED ' + char);
}

for (const char of charsArg) {
  probeCharacter(char);
}
