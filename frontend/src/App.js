import React, { useState } from 'react';
import axios from 'axios';

function App() {

    // Initialize all the states
    const [file, setFile] = useState(null);
    const [data, setData] = useState([]);
    const [userPrompt, setUserPrompt] = useState("");
    const [regex, setRegex] = useState("");
    const [replace, setReplace] = useState("");
    const [isTextVisible, setIsTextVisible] = useState(false);
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);


    const handleFileChange = (e) => setFile(e.target.files[0]);

    const uploadFile = async (page = 1) => {
        if (!file) {
            console.error("No file selected.");
            return;
        }
    
        const formData = new FormData();
        formData.append("file", file);

        if (typeof page === "object") {
            page = page.detail;
        }
    
        try {
            // Reset state before making request
            setRegex("");
            setReplace("");
            setIsTextVisible(false);
    
            // Send file to backend
            const res = await axios.post(`http://127.0.0.1:8000/upload/?page=${page}&page_size=10`, formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
    
            let responseData = res.data;
            
            if (typeof(responseData.data) != "undefined") {
                setData(responseData.data);
                setCurrentPage(responseData.current_page);
                setTotalPages(responseData.total_pages);
            } else {
                try {
                    // Handle possible NaN values safely
                    let fixedJsonString = responseData.replace(/NaN/g, "null");
                    let jsonData = JSON.parse(fixedJsonString);
                    setData(jsonData.data);
                    setCurrentPage(jsonData.current_page);
                    setTotalPages(jsonData.total_pages);
                } catch (error) {
                    console.error("Error parsing JSON:", error);
                }
            }
        } catch (error) {
            console.error("Upload failed:", error.response?.data || error.message);
        }
    };
    

    const handleGenerateRegex = async () => {
        if (!userPrompt.trim()) {
            console.error("User prompt is empty.");
            return;
        }
    
        setLoading(true);
        
        try {
            const response = await fetch("http://127.0.0.1:8000/generate_regex/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_prompt: userPrompt }),
            });
    
            if (!response.ok) {
                throw new Error(`Server Error: ${response.status} ${response.statusText}`);
            }
    
            const res = await response.json();
    
            if (res.regex_pattern && res.replace) {
                let pattern = res.regex_pattern.trim();
    
                // Ensure regex is extracted properly
                pattern = pattern.replaceAll("{'regex_pattern': '", "");
                pattern = pattern.replaceAll("{'regex_pattern':'", "");
                pattern = pattern.replaceAll(/\\\\/g, "\\");
                pattern = pattern.replaceAll("'}", "");
                pattern = pattern.replaceAll("'", "");
                pattern = pattern.replaceAll('\b', '');
    
                console.log("Generated Regex:", pattern);
    
                setRegex(pattern);
                setReplace(res.replace);
                setIsTextVisible(true);
    
                // Update JSON data
                const updatedJson = replaceMatchingValues(data, pattern, res.replace);
                setData(updatedJson);
            } else {
                console.error("Invalid response format:", res);
            }
        } catch (error) {
            console.error("Error generating regex:", error.message);
        } finally {
            setLoading(false);
        }
    };
    

    function replaceMatchingValues(json, regexString, replacement) {
        try {
            // Ensure regex string has word boundaries and is global
            // const regex = new RegExp(`\\b${regexString}\\b`, "g");
            const regex = new RegExp(regexString, "g");
    
            function traverse(obj) {
                if (Array.isArray(obj)) {
                    // Handle arrays properly
                    return obj.map(item => traverse(item));
                } else if (typeof obj === "object" && obj !== null) {
                    for (let key in obj) {
                        if (typeof obj[key] === "string" && regex.test(obj[key])) {
                            // obj[key] = replacement;
                            obj[key] = obj[key].replace(regex, replacement);
                        } else if (typeof obj[key] === "object") {
                            obj[key] = traverse(obj[key]); // Recursively traverse nested objects
                        }
                    }
                }
                return obj;
            }
    
            // Clone to avoid modifying original object
            return traverse(JSON.parse(JSON.stringify(json)));
    
        } catch (error) {
            console.error("Error in replaceMatchingValues:", error);
            return json; // Return original JSON if there's an error
        }
    }
    

    return (
        <div className="p-6 mx-auto">
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
                    className="ml-4 bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600"
                >
                    Upload
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

            <h3 className="text-xl font-semibold mt-6 mb-4">Excel/CSV Data</h3>

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
            {/* Pagination Controls */}
            <div className="mt-4 flex justify-between">
                <button
                    onClick={() => uploadFile(currentPage - 1)}
                    disabled={currentPage === 1}
                    className="bg-gray-500 text-white py-2 px-4 rounded-md hover:bg-gray-600 disabled:opacity-50"
                >
                    Previous
                </button>
                <span className="text-lg">Page {currentPage} of {totalPages}</span>
                <button
                    onClick={() => uploadFile(currentPage + 1)}
                    disabled={currentPage === totalPages}
                    className="bg-gray-500 text-white py-2 px-4 rounded-md hover:bg-gray-600 disabled:opacity-50"
                >
                    Next
                </button>
            </div>
        </div>
    );
}

export default App;
