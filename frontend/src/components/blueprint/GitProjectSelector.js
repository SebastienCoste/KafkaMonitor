import React, { useState, useEffect } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

export default function GitProjectSelector({ onProjectSelect, onCancel }) {
    const [gitUrl, setGitUrl] = useState('');
    const [branch, setBranch] = useState('main');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [existingProjects, setExistingProjects] = useState([]);
    const [loadingProjects, setLoadingProjects] = useState(true);

    useEffect(() => {
        loadExistingProjects();
    }, []);

    const loadExistingProjects = async () => {
        try {
            setLoadingProjects(true);
            const response = await axios.get(`${BACKEND_URL}/api/blueprint/integration/projects`);
            if (response.data.success) {
                setExistingProjects(response.data.projects || []);
            }
        } catch (err) {
            console.error('Failed to load existing projects:', err);
        } finally {
            setLoadingProjects(false);
        }
    };

    const handleAddProject = async () => {
        if (!gitUrl.trim()) {
            setError('Please enter a Git URL');
            return;
        }

        if (!branch.trim()) {
            setError('Please enter a branch name');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await axios.post(`${BACKEND_URL}/api/blueprint/integration/add-project`, {
                git_url: gitUrl,
                branch: branch
            });

            if (response.data.success && response.data.project) {
                // Notify parent component
                onProjectSelect(response.data.project);
            } else {
                setError(response.data.message || 'Failed to add project');
            }
        } catch (err) {
            console.error('Failed to add project:', err);
            setError(err.response?.data?.detail || 'Failed to add project. Please check the URL and try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectExisting = (project) => {
        onProjectSelect(project);
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="px-6 py-4 border-b border-gray-200">
                    <div className="flex justify-between items-center">
                        <h2 className="text-2xl font-semibold text-gray-800">Select Git Project</h2>
                        <button
                            onClick={onCancel}
                            className="text-gray-400 hover:text-gray-600 transition-colors"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="px-6 py-4">
                    {/* Existing Projects Section */}
                    <div className="mb-6">
                        <h3 className="text-lg font-semibold text-gray-800 mb-3">Existing Projects</h3>
                        
                        {loadingProjects ? (
                            <div className="text-center py-8 text-gray-500">
                                Loading projects...
                            </div>
                        ) : existingProjects.length > 0 ? (
                            <div className="space-y-2 max-h-64 overflow-y-auto">
                                {existingProjects.map((project) => (
                                    <div
                                        key={project.id}
                                        className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-all cursor-pointer"
                                        onClick={() => handleSelectExisting(project)}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <h4 className="text-sm font-semibold text-gray-800 truncate">{project.name}</h4>
                                            <p className="text-xs text-gray-500 truncate">{project.git_url}</p>
                                            <div className="flex items-center gap-3 mt-1">
                                                <span className="text-xs text-gray-600">
                                                    <span className="font-medium">Branch:</span> {project.branch}
                                                </span>
                                                <span className={`text-xs px-2 py-0.5 rounded ${
                                                    project.status === 'clean' 
                                                        ? 'bg-green-100 text-green-700' 
                                                        : 'bg-yellow-100 text-yellow-700'
                                                }`}>
                                                    {project.status}
                                                </span>
                                            </div>
                                        </div>
                                        <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                        </svg>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="text-center py-8 text-gray-500 border border-gray-200 rounded-lg">
                                No existing projects. Add a new project below.
                            </div>
                        )}
                    </div>

                    <div className="border-t border-gray-200 pt-6">
                        <h3 className="text-lg font-semibold text-gray-800 mb-4">Add New Git Project</h3>

                        {/* Git URL Input */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Git Repository URL
                            </label>
                            <input
                                type="text"
                                value={gitUrl}
                                onChange={(e) => setGitUrl(e.target.value)}
                                placeholder="https://github.com/user/repo.git"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                disabled={loading}
                            />
                            <p className="text-xs text-gray-500 mt-1">
                                Enter a public Git repository URL (HTTPS or SSH)
                            </p>
                        </div>

                        {/* Branch Input */}
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Branch
                            </label>
                            <input
                                type="text"
                                value={branch}
                                onChange={(e) => setBranch(e.target.value)}
                                placeholder="main"
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                disabled={loading}
                            />
                        </div>

                        {/* Error Message */}
                        {error && (
                            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                                <p className="text-sm text-red-700">{error}</p>
                            </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={onCancel}
                                className="px-6 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                                disabled={loading}
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddProject}
                                disabled={loading || !gitUrl.trim() || !branch.trim()}
                                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                            >
                                {loading ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                        </svg>
                                        Adding...
                                    </>
                                ) : (
                                    <>
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                        </svg>
                                        Add Project
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
