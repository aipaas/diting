import { useState } from "react";
import type { CaseType } from "../types/Cases";

const useFilterCases = (cases: CaseType[]) => {
	const [searchTerm, setSearchTerm] = useState<string>("");

	const filteredCases = cases.filter(
		(case_) =>
			case_.input.toLowerCase().includes(searchTerm.toLowerCase()) ||
			case_.actual_output.toLowerCase().includes(searchTerm.toLowerCase()),
	);

	return { filteredCases, searchTerm, setSearchTerm };
};

export default useFilterCases;
