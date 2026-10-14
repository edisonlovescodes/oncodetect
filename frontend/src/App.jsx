import { useEffect, useRef, useState } from "react";
import "./App.css";

const API = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/$/, "");
const source = "https://github.com/edisonlovescodes/oncodetect";

async function request(path, options) {
  const response = await fetch(`${API}${path}`, options);
  const body = await response.json();
  if (!response.ok)
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Request could not be completed",
    );
  return body;
}

function Arrow({ diagonal = false }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d={diagonal ? "M6 18 18 6M6 6h12v12" : "M4 12h15m-6-6 6 6-6 6"} />
    </svg>
  );
}

export default function App() {
  const input = useRef(null);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");
  const [service, setService] = useState("checking");
  const [dragging, setDragging] = useState(false);

  async function refreshRecords() {
    const records = await Promise.allSettled([
      request("/predictions?limit=5"),
      request("/stats"),
    ]);
    if (records[0].status === "fulfilled")
      setHistory(records[0].value.predictions || []);
    if (records[1].status === "fulfilled") setStats(records[1].value);
  }
  useEffect(() => {
    refreshRecords();
    let active = true;
    request("/health")
      .then((body) => {
        if (active) setService(body.model_loaded ? "ready" : "unavailable");
      })
      .catch(() => {
        if (active) setService("unavailable");
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(next) {
    if (!next || loading) return;
    setError("");
    if (!["image/png", "image/jpeg"].includes(next.type)) {
      setError("Choose a PNG or JPEG image.");
      return;
    }
    if (next.size > 8 * 1024 * 1024) {
      setError("The image must be smaller than 8 MiB.");
      return;
    }
    setFile(next);
    setResult(null);
  }
  function reset() {
    setFile(null);
    setResult(null);
    setError("");
    if (input.current) input.current.value = "";
  }
  async function analyze() {
    if (!file || loading) return;
    setLoading(true);
    setError("");
    const body = new FormData();
    body.append("file", file);
    try {
      setResult(await request("/predict", { method: "POST", body }));
      setService("ready");
      await refreshRecords();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="onco-page">
      <a className="skip-link" href="#workspace">
        Skip to workspace
      </a>
      <header className="masthead">
        <a href="#" className="wordmark" aria-label="OncoDetect home">
          <span className="onco-mark" aria-hidden="true">
            <i />
            <i />
          </span>
          OncoDetect<span className="wordmark-dot">.</span>
        </a>
        <div className="masthead-right">
          <span className="edition">IMAGE STUDIES / 01</span>
          <a href={source} target="_blank" rel="noreferrer">
            Source code <Arrow diagonal />
          </a>
        </div>
      </header>

      <main>
        <section className="intro" aria-labelledby="title">
          <div>
            <p className="eyebrow">LUNG NODULE CLASSIFICATION</p>
            <h1 id="title">
              A closer <em>look.</em>
            </h1>
          </div>
          <div className="intro-note">
            <span className="small-rule" />
            <p>
              One cropped image.
              <br />A considered, traceable result.
            </p>
            <span>
              Upload a nodule crop, review its model score, and keep a record of
              the analysis.
            </span>
          </div>
        </section>
        <div className="workspace-meta">
          <span>
            <b>01</b> IMAGE WORKSPACE
          </span>
          <span className={`service ${service}`}>
            <i />
            {service === "ready"
              ? "Model available"
              : service === "checking"
                ? "Checking connection"
                : "Model unavailable"}
          </span>
        </div>
        <section
          id="workspace"
          className="workspace"
          aria-label="Image classification workspace"
        >
          <div className="intake">
            <div className="section-label">
              <span>INPUT</span>
              <span>01 / 03</span>
            </div>
            <h2>
              Start with
              <br />
              the image.
            </h2>
            <p className="intake-description">
              A PNG or JPEG crop of a lung nodule. Whole CT volumes are not
              supported.
            </p>
            <div
              className={`drop-zone ${dragging ? "dragging" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                if (!loading) setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                selectFile(e.dataTransfer.files[0]);
              }}
            >
              <svg
                className="upload-icon"
                viewBox="0 0 44 44"
                fill="none"
                aria-hidden="true"
              >
                <path d="M22 29V8m-7 7 7-7 7 7M9 27v9h26v-9" />
              </svg>
              <input
                ref={input}
                className="sr-only"
                aria-label="Choose Image"
                type="file"
                accept="image/png,image/jpeg"
                disabled={loading}
                onChange={(e) => selectFile(e.target.files[0])}
              />
              <button
                className="select-button"
                onClick={() => input.current?.click()}
                disabled={loading}
              >
                {file ? "Replace image" : "Choose Image"}
                <Arrow diagonal />
              </button>
              <span className="drop-hint">
                or drop a file here · up to 8 MiB
              </span>
            </div>
            <div className="file-meta">
              <span>{file ? file.name : "No image selected"}</span>
              <span>
                {file ? `${(file.size / 1024).toFixed(1)} KB` : "PNG / JPG"}
              </span>
            </div>
            <button
              className="analyze-button"
              disabled={!file || loading}
              onClick={analyze}
            >
              {loading ? "Analyzing…" : "Analyze"}
              <Arrow />
            </button>
            <button
              className="reset-button"
              onClick={reset}
              disabled={!file || loading}
            >
              Clear workspace
            </button>
            {error && (
              <p className="error-note" role="alert">
                {error}
              </p>
            )}
            <p className="research-note">
              Research prototype. Model scores are not calibrated clinical
              probabilities.
            </p>
          </div>

          <div className="view-and-result">
            <div className="image-viewer" aria-label="Image preview">
              <div className="viewer-top">
                <span>IMAGE VIEWPORT</span>
                <span>{preview ? "CROP LOADED" : "AWAITING INPUT"}</span>
              </div>
              <div className="image-stage">
                <div className={`crop-frame ${preview ? "has-image" : ""}`}>
                  <i className="corner tl" />
                  <i className="corner tr" />
                  <i className="corner bl" />
                  <i className="corner br" />
                  {preview ? (
                    <img src={preview} alt="Selected nodule crop" />
                  ) : (
                    <div className="empty-crop">
                      <div className="crop-cross" />
                      <p>The image comes first.</p>
                      <span>Your crop will appear here.</span>
                    </div>
                  )}
                </div>
                <div className="scale-mark" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                  <i />
                </div>
              </div>
              <div className="viewer-bottom">
                <span>{preview ? "ORIGINAL UPLOAD" : "NO IMAGE LOADED"}</span>
                <span>224 × 224 MODEL INPUT</span>
              </div>
            </div>
            <div
              className={`result-panel ${result ? "complete" : ""}`}
              aria-live="polite"
            >
              <div>
                <div className="section-label">
                  <span>MODEL OUTPUT</span>
                  <span>02 / 03</span>
                </div>
                {result ? (
                  <h3>{result.prediction}</h3>
                ) : (
                  <h3>
                    {loading ? "Reading the crop…" : "Ready when you are."}
                  </h3>
                )}
              </div>
              {result ? (
                <div className="result-score">
                  <span>Model score: {result.confidence}%</span>
                  <p>
                    Record #{result.prediction_id} ·{" "}
                    {new Date(result.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              ) : (
                <p className="output-note">
                  Select an image and run the model
                  <br />
                  to create a recorded result.
                </p>
              )}
            </div>
          </div>
        </section>

        <section className="records" aria-labelledby="records-title">
          <div className="records-heading">
            <div>
              <p className="eyebrow">03 / ANALYSIS RECORD</p>
              <h2 id="records-title">The latest observations.</h2>
            </div>
            <p>
              {stats ? (
                <>
                  <strong>{stats.total_predictions}</strong> total recorded
                  <br />
                  <span>
                    {stats.benign_count} benign · {stats.malignant_count}{" "}
                    malignant
                  </span>
                </>
              ) : (
                "Records appear when the service is connected."
              )}
            </p>
          </div>
          {history.length ? (
            <div className="records-table">
              <table>
                <thead>
                  <tr>
                    <th>RECORD</th>
                    <th>IMAGE</th>
                    <th>MODEL LABEL</th>
                    <th>MODEL SCORE</th>
                    <th>TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr key={item.id}>
                      <td>#{String(item.id).padStart(3, "0")}</td>
                      <td>{item.filename}</td>
                      <td>{item.prediction}</td>
                      <td>{item.confidence}%</td>
                      <td>
                        {new Date(item.timestamp).toLocaleString([], {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-records">
              <span>—</span>
              <p>No observations yet. Your first analysis starts the record.</p>
            </div>
          )}
        </section>
      </main>
      <footer>
        <span>ONCODETECT / IMAGE CLASSIFICATION PROTOTYPE</span>
        <span>
          Built by Edison Essien{" "}
          <a href={source} target="_blank" rel="noreferrer">
            <Arrow diagonal />
          </a>
        </span>
      </footer>
    </div>
  );
}
