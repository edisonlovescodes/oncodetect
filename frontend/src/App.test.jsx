import { vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "./App.jsx";

const response = (body, ok = true) =>
  Promise.resolve({ ok, json: () => Promise.resolve(body) });

beforeEach(() => {
  URL.createObjectURL = vi.fn(() => "blob:test-crop");
  URL.revokeObjectURL = vi.fn();
  global.fetch = vi.fn((url) => {
    if (url.includes("/predictions")) return response({ predictions: [] });
    if (url.endsWith("/stats"))
      return response({
        total_predictions: 0,
        benign_count: 0,
        malignant_count: 0,
      });
    return response({
      prediction: "Benign",
      confidence: 70,
      prediction_id: 1,
      timestamp: "2026-10-13T12:00:00Z",
    });
  });
});

afterEach(() => vi.restoreAllMocks());

test("uploads a nodule crop to the same-origin API and shows the model score", async () => {
  render(<App />);
  expect(screen.getByRole("button", { name: "Analyze" })).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Choose Image"), {
    target: {
      files: [new File(["fixture"], "crop.png", { type: "image/png" })],
    },
  });
  fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
  expect(await screen.findByText("Model score: 70%")).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith(
    "/api/predict",
    expect.objectContaining({ method: "POST", body: expect.any(FormData) }),
  );
  expect(screen.queryByText("Attention Heatmap")).not.toBeInTheDocument();
});

test("shows the actual API error and re-enables the button", async () => {
  global.fetch.mockImplementation((url) =>
    url.endsWith("/predict")
      ? response({ detail: "Model unavailable" }, false)
      : response(url.includes("/predictions") ? { predictions: [] } : {}),
  );
  render(<App />);
  fireEvent.change(screen.getByLabelText("Choose Image"), {
    target: { files: [new File(["x"], "crop.png", { type: "image/png" })] },
  });
  fireEvent.click(screen.getByRole("button", { name: "Analyze" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Model unavailable",
  );
  await waitFor(() =>
    expect(screen.getByRole("button", { name: "Analyze" })).not.toBeDisabled(),
  );
});

test("rejects unsupported image types before contacting the model", () => {
  render(<App />);
  fireEvent.change(screen.getByLabelText("Choose Image"), {
    target: {
      files: [new File(["text"], "notes.txt", { type: "text/plain" })],
    },
  });
  expect(screen.getByRole("alert")).toHaveTextContent(
    "Choose a PNG or JPEG image.",
  );
  expect(
    screen.getByRole("button", { name: "Analyze", exact: true }),
  ).toBeDisabled();
});

test("clearing the workspace removes the selected image", () => {
  render(<App />);
  fireEvent.change(screen.getByLabelText("Choose Image"), {
    target: {
      files: [new File(["fixture"], "crop.png", { type: "image/png" })],
    },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Clear workspace", exact: true }),
  );
  expect(
    screen.getByRole("button", { name: "Analyze", exact: true }),
  ).toBeDisabled();
  expect(screen.getByText("No image selected")).toBeInTheDocument();
});
