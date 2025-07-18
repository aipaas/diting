import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';

export default defineConfig({
	html: {
		title: 'DiTing',
	},
	plugins: [pluginReact()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000',
		},
	},
});
