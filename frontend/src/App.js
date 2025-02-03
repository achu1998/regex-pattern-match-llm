import React, { useState } from 'react';
import axios from 'axios';

function App() {
    const [file, setFile] = useState(null);
    const [data, setData] = useState([]);
    const [userPrompt, setUserPrompt] = useState("");
    const [text, setText] = useState("");

    const handleFileChange = (e) => setFile(e.target.files[0]);

    const uploadFile = async () => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            setText("");
            const res = await axios.post('http://127.0.0.1:8000/upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setData(res.data.data);
        } catch (error) {
            console.error(error);
        }
    };

    const fetchData = async () => {
        setText("");
        const res = await axios.get('http://127.0.0.1:8000/data/');
        setData(res.data.data);
    };

    const handleGenerateRegex = async () => {
        const response = await fetch("http://127.0.0.1:8000/generate_regex/", {
          method: "POST",
          headers: { "Content-Type": "text" },
          body: JSON.stringify({ user_prompt: userPrompt }),
        });
    
        const res = await response.json();
        if(res.regex_pattern && res.replace) {
            var pattern = res.regex_pattern;
            console.log(pattern);
            pattern = pattern.replaceAll("{'regex_pattern': '", "");
            pattern = pattern.replaceAll("{'regex_pattern':'", "");
            pattern = pattern.replaceAll("'}", "");
            pattern = pattern.replaceAll("'", "");
            setText(pattern);
            const updatedJson = replaceMatchingValues(data, pattern, res.replace);
            setData(updatedJson);
        }
      };

      function replaceMatchingValues(json, regexString, replacement) {
        const regex = new RegExp(regexString);
        function traverse(obj) {
            if (typeof obj === "object" && obj !== null) {
                for (let key in obj) {
                    if (typeof obj[key] === "string" && regex.test(obj[key])) {
                        console.log(obj[key]);
                        obj[key] = replacement;
                    } else if (typeof obj[key] === "object") {
                        traverse(obj[key]); // Recursively traverse nested objects/arrays
                    }
                }
            }
        }
    
        let clonedJson = JSON.parse(JSON.stringify(json)); // Clone to avoid modifying original object
        traverse(clonedJson);
        return clonedJson;
    }

    return (
        <div>
            <h2>Upload Excel File</h2>
            <input type="file" onChange={handleFileChange} />
            <button onClick={uploadFile}>Upload</button>
            <button onClick={fetchData}>Fetch Stored Data</button>
            <br />
            <br />
            <input
                type="text"
                placeholder="Enter your instruction (e.g., Find emails...)"
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
            />
            <button onClick={handleGenerateRegex}>Generate Regex</button>

            <p className="regexClass">{text}</p>
            <h3>Excel Data</h3>
            <table border="1">
                <thead>
                    {Array.isArray(data) && data.length > 0 && (
                        <tr>
                            {Object.keys(data[0]).map((key) => (
                                <th key={key}>{key}</th>
                            ))}
                        </tr>
                    )}
                </thead>
                <tbody>
                    {Array.isArray(data) && data.map((row, idx) => (
                        <tr key={idx}>
                            {Object.values(row).map((val, i) => (
                                <td key={i}>{val}</td>
                            ))}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

export default App;
