use std::collections::HashMap;
use std::path::Path;

use serde::Deserialize;

#[derive(Debug, Deserialize, Default, Clone)]
pub struct Config {
    #[serde(default)]
    pub select: Vec<String>,
    #[serde(default)]
    pub ignore: Vec<String>,
    #[serde(default)]
    pub exclude: Vec<String>,
    #[serde(default, rename = "per-file-ignores")]
    pub per_file_ignores: HashMap<String, Vec<String>>,
}

#[derive(Debug, Deserialize)]
struct PyprojectToml {
    tool: Option<ToolSection>,
}

#[derive(Debug, Deserialize)]
struct ToolSection {
    #[serde(rename = "jg-linter")]
    jg_linter: Option<Config>,
}

impl Config {
    pub fn is_rule_selected(&self, code: &str) -> bool {
        if self.select.is_empty() {
            return true;
        }
        self.select.iter().any(|s| code.starts_with(s.as_str()))
    }

    pub fn is_rule_ignored(&self, code: &str, file_path: &Path) -> bool {
        if self.ignore.iter().any(|s| code.starts_with(s.as_str())) {
            return true;
        }
        let fp = file_path.to_string_lossy();
        for (pattern, codes) in &self.per_file_ignores {
            if let Ok(pat) = glob::Pattern::new(pattern) {
                if pat.matches(&fp) && codes.iter().any(|c| code.starts_with(c.as_str())) {
                    return true;
                }
            }
        }
        false
    }

    pub fn effective_exclude(&self) -> Vec<String> {
        if self.exclude.is_empty() {
            vec![
                ".venv/**".to_string(),
                "__pycache__/**".to_string(),
                "*.egg-info/**".to_string(),
                ".git/**".to_string(),
            ]
        } else {
            self.exclude.clone()
        }
    }
}

pub fn load_config(project_root: &Path) -> Config {
    let path = if project_root.is_file()
        && project_root
            .file_name()
            .is_some_and(|f| f == "pyproject.toml")
    {
        project_root.to_path_buf()
    } else {
        project_root.join("pyproject.toml")
    };

    let Ok(content) = std::fs::read_to_string(&path) else {
        return Config::default();
    };
    let Ok(parsed) = toml::from_str::<PyprojectToml>(&content) else {
        return Config::default();
    };
    parsed.tool.and_then(|t| t.jg_linter).unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_select_enables_all() {
        let config = Config::default();
        assert!(config.is_rule_selected("JG001"));
        assert!(config.is_rule_selected("PLUGIN001"));
    }

    #[test]
    fn select_by_exact_code() {
        let config = Config {
            select: vec!["JG001".to_string()],
            ..Default::default()
        };
        assert!(config.is_rule_selected("JG001"));
        assert!(!config.is_rule_selected("JG002"));
    }

    #[test]
    fn select_by_prefix() {
        let config = Config {
            select: vec!["JG".to_string()],
            ..Default::default()
        };
        assert!(config.is_rule_selected("JG001"));
        assert!(config.is_rule_selected("JG999"));
        assert!(!config.is_rule_selected("PLUGIN001"));
    }

    #[test]
    fn ignore_by_code() {
        let config = Config {
            ignore: vec!["JG001".to_string()],
            ..Default::default()
        };
        assert!(config.is_rule_ignored("JG001", Path::new("foo.py")));
        assert!(!config.is_rule_ignored("JG002", Path::new("foo.py")));
    }

    #[test]
    fn per_file_ignores() {
        let mut pfi = HashMap::new();
        pfi.insert("tests/**".to_string(), vec!["JG001".to_string()]);
        let config = Config {
            per_file_ignores: pfi,
            ..Default::default()
        };
        assert!(config.is_rule_ignored("JG001", Path::new("tests/test_foo.py")));
        assert!(!config.is_rule_ignored("JG001", Path::new("src/foo.py")));
    }

    #[test]
    fn parse_pyproject_toml() {
        let content = r#"
[tool.jg-linter]
select = ["JG"]
ignore = ["JG003"]
exclude = [".venv/**"]

[tool.jg-linter.per-file-ignores]
"tests/**" = ["JG001"]
"#;
        let parsed: PyprojectToml = toml::from_str(content).unwrap();
        let config = parsed.tool.unwrap().jg_linter.unwrap();
        assert_eq!(config.select, vec!["JG"]);
        assert_eq!(config.ignore, vec!["JG003"]);
        assert_eq!(config.exclude, vec![".venv/**"]);
        assert!(config.per_file_ignores.contains_key("tests/**"));
    }

    #[test]
    fn default_excludes() {
        let config = Config::default();
        let exc = config.effective_exclude();
        assert!(exc.contains(&".venv/**".to_string()));
        assert!(exc.contains(&"__pycache__/**".to_string()));
    }
}
