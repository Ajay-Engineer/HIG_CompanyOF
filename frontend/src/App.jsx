import { useState } from "react";
import "./App.css";

function App() {
  const [companyName, setCompanyName] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false); // 🚀 New loading state

  const fetchCompanyInfo = async () => {
    if (!companyName.trim()) return;

    setLoading(true);      // 🔄 Start loading
    setResult(null);       // Optional: clear old result

    try {
      const res = await fetch("http://localhost:5000/company", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company_name: companyName }),
      });

      const data = await res.json();
      setResult({ ...data, parsedData: data.data });
    } catch (err) {
      console.error("API call failed", err);
      setResult({ error: "Failed to fetch data. Please try again." });
    } finally {
      setLoading(false); // ✅ Done loading
    }
  };

  return (
    <div className="app">
      <h1>Company Info Lookup</h1>
      <input
        type="text"
        placeholder="Enter company name"
        value={companyName}
        onChange={(e) => setCompanyName(e.target.value)}
      />
      <button onClick={fetchCompanyInfo}>Search</button>

      {/* 🔄 Loading message */}
      {loading && <p style={{ marginTop: "1rem", color: "#555" }}>🔍 Fetching data, please wait...</p>}

      {/* ✅ Display result once loaded */}
      {!loading && result && result.parsedData ? (
        <div className="result">
          <h2>Source: {result.source}</h2>
          <h3>{result.parsedData.company_name}</h3>
          <p><strong>Founded:</strong> {result.parsedData.founded_year}</p>
          <p><strong>Headquarters:</strong> {result.parsedData.headquarters_location}</p>
          <p><strong>Branches:</strong> {Array.isArray(result.parsedData.branch_locations) ? result.parsedData.branch_locations.join(", ") : result.parsedData.branch_locations}</p>
          <p><strong>Core Focus:</strong> {result.parsedData.core_business_or_main_focus}</p>
          <p><strong>Company Culture:</strong> {result.parsedData.company_culture_summary}</p>

          <div>
            <strong>Pros of Working There:</strong>
            <div>
              {Array.isArray(result.parsedData.pros_of_working_there) &&
                result.parsedData.pros_of_working_there.map((item, index) => (
                  <div key={index} className="list-none">{item}</div>
              ))}
            </div>
          </div>

          <div>
            <strong>Cons of Working There:</strong>
            <div>
              {Array.isArray(result.parsedData.cons_of_working_there) &&
                result.parsedData.cons_of_working_there.map((item, index) => (
                  <div key={index} className="list-none">{item}</div>
              ))}
            </div>
          </div>

          <div className="rating-box">
            <h3 style={{ fontSize: 40 }}>
              🎯 Fresher-Friendly Rating: {result.parsedData.fresher_friendly_rating_percent}%
            </h3>
            <p style={{ fontStyle: "italic", fontSize: "0.9rem" }}>
              Based on learning opportunities, growth, and company culture for new joiners.
            </p>
          </div>
        </div>
      ) : !loading && result?.error ? (
        <div className="result">
          <h2>Error</h2>
          <p>{result.error}</p>
        </div>
      ) : null}
    </div>
  );
}

export default App;
