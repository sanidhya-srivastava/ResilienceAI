import "@testing-library/jest-dom/vitest";

// Recharts ResponsiveContainer relies on ResizeObserver, which jsdom omits.
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
