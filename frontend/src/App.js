import React, { useState } from 'react';
import axios from 'axios';

function App() {
    const [file, setFile] = useState(null);
    const [data, setData] = useState([]);
    const [userPrompt, setUserPrompt] = useState("");
    const [regex, setRegex] = useState("");
    const [replace, setReplace] = useState("");
    const [isTextVisible, setIsTextVisible] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleFileChange = (e) => setFile(e.target.files[0]);

    const uploadFile = async () => {
        const formData = new FormData();
        formData.append('file', file);

        try {
            setRegex("");
            setReplace("");
            setIsTextVisible(false);
            const res = await axios.post('http://127.0.0.1:8000/upload/', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            setData(res.data.data);
        } catch (error) {
            console.error(error);
        }
    };

    const fetchData = async () => {
        setRegex("");
        setReplace("");
        setIsTextVisible(false);
        const res = await axios.get('http://127.0.0.1:8000/data/');
        setData(res.data.data);
    };

    const handleGenerateRegex = async () => {
        setLoading(true);
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
            setRegex(pattern);
            setReplace(res.replace);
            setIsTextVisible(true);
            setLoading(false);
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
        <div className="p-6 max-w-4xl mx-auto">
            <h2 className="text-2xl font-semibold mb-4">Upload Excel File</h2>
            <div className="mb-4">
                <input 
                    type="file" 
                    onChange={handleFileChange} 
                    className="border-2 border-gray-300 p-2 rounded-md"
                />
            </div>
            <div className="mb-4">
                <button 
                    onClick={uploadFile} 
                    className="bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
                >
                    Upload
                </button>
                <button 
                    onClick={fetchData} 
                    className="ml-4 bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600"
                >
                    Fetch Stored Data
                </button>
            </div>

            <div className="mb-4">
                <input 
                    type="text" 
                    placeholder="Enter your instruction (e.g., Find emails...)"
                    value={userPrompt}
                    onChange={(e) => setUserPrompt(e.target.value)}
                    className="border-2 border-gray-300 p-2 rounded-md w-full mb-2"
                />
                <button 
                    onClick={handleGenerateRegex} 
                    className="bg-indigo-500 text-white py-2 px-4 rounded-md hover:bg-indigo-600"
                >
                    Generate Regex
                </button>
            </div>

            <p className={`mt-4 text-lg text-gray-700 ${isTextVisible ? '' : 'hidden'}`}>
                <b>Regex Pattern: </b>{regex}
            </p>

            <p className={`mt-4 text-lg text-gray-700 ${isTextVisible ? '' : 'hidden'}`}>
                <b>Replacement Value: </b>{replace}
            </p>

            <h3 className="text-xl font-semibold mt-6 mb-4">Excel Data</h3>

            {/* Loader: Visible when loading is true */}
            {loading && (
                <div className="absolute inset-0 bg-gray-500 bg-opacity-50 flex items-center justify-center z-10">
                    <div className="animate-spin rounded-full border-t-4 border-blue-500 border-solid w-16 h-16"></div>
                </div>
            )}

            <div className="relative">
                <table className="min-w-full border-collapse border border-gray-300">
                    <thead>
                        {Array.isArray(data) && data.length > 0 && (
                            <tr>
                                {Object.keys(data[0]).map((key) => (
                                    <th key={key} className="px-4 py-2 border-b bg-gray-100 text-left">{key}</th>
                                ))}
                            </tr>
                        )}
                    </thead>
                    <tbody>
                        {Array.isArray(data) && data.map((row, idx) => (
                            <tr key={idx} className="hover:bg-gray-100">
                                {Object.values(row).map((val, i) => (
                                    <td key={i} className="px-4 py-2 border-b">{val}</td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default App;
