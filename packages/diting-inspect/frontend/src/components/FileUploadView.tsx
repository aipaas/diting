import { useState } from 'react';
import { API_BASE } from '../constants';

const FileUploadView = ({ onSuccess }) => {
	const [file, setFile] = useState(null);

	const handleFileChange = (e) => {
		setFile(e.target.files[0]);
	};

	const handleUpload = async () => {
		if (!file) return;

		const formData = new FormData();
		formData.append('file', file);

		try {
			const response = await fetch(`${API_BASE}/cases/import`, {
				method: 'POST',
				body: formData,
			});
			if (response.ok) {
				onSuccess();
				alert('File uploaded successfully!');
			} else {
				alert('Failed to upload file');
			}
		} catch (error) {
			alert('Error uploading file');
		}
	};

	return (
		<div>
			<h2 className="text-xl font-semibold mb-4">Upload Cases</h2>
			<input type="file" onChange={handleFileChange} />
			<button onClick={handleUpload} className="mt-2 bg-blue-600 text-white px-4 py-2 rounded">
				Upload
			</button>
		</div>
	);
};

export default FileUploadView;
