use pyo3::prelude::*;
use std::fmt;

#[pyclass(from_py_object)]
#[derive(Clone, Debug)]
pub struct Violation {
    #[pyo3(get)]
    pub file_path: String,
    #[pyo3(get)]
    pub line: usize,
    #[pyo3(get)]
    pub col: usize,
    #[pyo3(get)]
    pub code: String,
    #[pyo3(get)]
    pub message: String,
}

#[pymethods]
impl Violation {
    #[new]
    fn new(file_path: String, line: usize, col: usize, code: String, message: String) -> Self {
        Self {
            file_path,
            line,
            col,
            code,
            message,
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "Violation({}, {}, {}, {}, {})",
            self.file_path, self.line, self.col, self.code, self.message
        )
    }

    fn __str__(&self) -> String {
        format!(
            "{}:{}:{}: {} {}",
            self.file_path, self.line, self.col, self.code, self.message
        )
    }
}

impl fmt::Display for Violation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}:{}:{}: {} {}",
            self.file_path, self.line, self.col, self.code, self.message,
        )
    }
}
