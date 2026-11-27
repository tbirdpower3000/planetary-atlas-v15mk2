// A stand-in for the MediaPipe hand finder, served in place of vision_bundle.mjs by tests/vr_hands.test.cjs.
// It behaves like the real one in the way that matters to these tests: handed a time that is not later than the last,
// it throws, and then throws on every later call until a new finder is made. window.__fake = { on, u, v, pinch, fail }
// places the hand; fail = true breaks the finder in use, as a lost graphics context would. window.__mp counts.
export const FilesetResolver = { forVisionTasks: async () => ({}) };
const T = [3, 33, -3, 29, -8, 24, -11, 19, -13, 15, -2, 16, -1, 10, 0, 5, 0, 0, 3, 15, 3.5, 8, 4, 2, 4, -2, 7, 16, 8, 10, 8.5, 5, 9, 1, 10, 19, 11.5, 14, 12.5, 10, 13, 7];
export const HandLandmarker = {
  createFromOptions: async () => {
    const M = (window.__mp = window.__mp || { made: 0, calls: 0, throws: 0, repeats: 0, closed: 0 });
    M.made++;
    let last = -Infinity, broken = false;
    return {
      close() { M.closed++; },
      detectForVideo(src, now) {
        const f = window.__fake || { on: false };
        M.calls++;
        if (f.fail) { broken = true; f.fail = false; }
        if (now <= last) { M.repeats++; broken = true; }
        if (broken) { M.throws++; throw new Error('stand-in: Packet timestamp mismatch'); }
        last = now;
        if (!f.on) return { landmarks: [], worldLandmarks: [], handednesses: [] };
        const lm = Array.from({ length: 21 }, (_, i) => ({ x: f.u + T[i * 2] * 0.01 * 0.5625, y: f.v + T[i * 2 + 1] * 0.01, z: 0 }));
        const w = lm.map((p) => ({ x: p.x, y: p.y, z: 0 }));
        if (f.pinch) w[4] = { x: w[8].x + 0.005, y: w[8].y, z: 0 };
        return { landmarks: [lm], worldLandmarks: [w], handednesses: [[{ categoryName: 'Right' }]] };
      },
    };
  },
};
