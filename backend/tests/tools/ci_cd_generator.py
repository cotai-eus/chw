"""
CI/CD Configuration Generator for Testing Infrastructure.
Generates GitHub Actions and Jenkins pipeline configurations.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from tests.config.test_config import TestConfig, TestCategory, TestEnvironment

@dataclass 
class CIConfig:
    """CI/CD configuration parameters."""
    project_name: str = "licitacao-backend"
    python_version: str = "3.12"
    poetry_version: str = "1.8.2"
    cache_key_version: str = "v1"
    
class CIConfigGenerator:
    """Generate CI/CD configurations for the testing infrastructure."""
    
    def __init__(self, config: TestConfig, ci_config: CIConfig = None):
        self.config = config
        self.ci_config = ci_config or CIConfig()
        self.output_dir = Path(__file__).parent.parent.parent
    
    def generate_github_actions(self) -> Dict[str, Any]:
        """Generate GitHub Actions workflow configuration."""
        workflow = {
            "name": "Comprehensive Testing Pipeline",
            "on": {
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main", "develop"]},
                "workflow_dispatch": {},
                "schedule": [{"cron": "0 2 * * *"}]  # Daily at 2 AM
            },
            "env": {
                "POETRY_VERSION": self.ci_config.poetry_version,
                "PYTHON_VERSION": self.ci_config.python_version
            },
            "jobs": self._generate_github_jobs()
        }
        return workflow
    
    def _generate_github_jobs(self) -> Dict[str, Any]:
        """Generate GitHub Actions jobs."""
        jobs = {
            "validate-infrastructure": {
                "name": "Validate Testing Infrastructure", 
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    self._get_python_setup_step(),
                    self._get_poetry_setup_step(),
                    self._get_dependency_install_step(),
                    {
                        "name": "Validate Infrastructure",
                        "run": "poetry run python tests/test_manager.py --validate"
                    }
                ]
            }
        }
        
        # Add test category jobs
        test_jobs = self._generate_test_category_jobs()
        jobs.update(test_jobs)
        
        # Add reporting job
        jobs["test-report"] = self._generate_reporting_job()
        
        return jobs
    
    def _generate_test_category_jobs(self) -> Dict[str, Any]:
        """Generate jobs for each test category."""
        jobs = {}
        
        for category in self.config.get_enabled_categories():
            config = self.config.get_category_config(category)
            
            job_name = f"test-{category.value}"
            jobs[job_name] = {
                "name": f"Test {config.name}",
                "runs-on": "ubuntu-latest",
                "needs": ["validate-infrastructure"],
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    self._get_python_setup_step(),
                    self._get_poetry_setup_step(),
                    self._get_dependency_install_step(),
                    self._get_service_setup_steps(category),
                    {
                        "name": f"Run {config.name}",
                        "run": f"poetry run python tests/test_manager.py --categories {category.value}",
                        "timeout-minutes": config.timeout_seconds // 60 + 5
                    },
                    self._get_artifact_upload_step(category)
                ]
            }
            
            # Add environment variables if needed
            env_vars = self.config.get_environment_setup(category)
            if env_vars:
                jobs[job_name]["env"] = env_vars
        
        return jobs
    
    def _get_python_setup_step(self) -> Dict[str, Any]:
        """Get Python setup step."""
        return {
            "name": "Set up Python",
            "uses": "actions/setup-python@v4",
            "with": {"python-version": self.ci_config.python_version}
        }
    
    def _get_poetry_setup_step(self) -> Dict[str, Any]:
        """Get Poetry setup step."""
        return {
            "name": "Install Poetry",
            "uses": "snok/install-poetry@v1",
            "with": {
                "version": self.ci_config.poetry_version,
                "virtualenvs-create": True,
                "virtualenvs-in-project": True,
                "installer-parallel": True
            }
        }
    
    def _get_dependency_install_step(self) -> Dict[str, Any]:
        """Get dependency installation step."""
        return {
            "name": "Install dependencies",
            "run": "poetry install --no-interaction --no-ansi"
        }
    
    def _get_service_setup_steps(self, category: TestCategory) -> Dict[str, Any]:
        """Get service setup steps for category."""
        config = self.config.get_category_config(category)
        
        if not config.dependencies:
            return {"name": "No additional services needed", "run": "echo 'No services to setup'"}
        
        services = []
        
        if "postgresql" in config.dependencies:
            services.append({
                "name": "Setup PostgreSQL",
                "run": """
                sudo systemctl start postgresql.service
                sudo -u postgres createuser --createdb --superuser $USER
                createdb test_db
                """
            })
        
        if "redis" in config.dependencies:
            services.append({
                "name": "Setup Redis",
                "run": """
                sudo systemctl start redis-server
                redis-cli ping
                """
            })
        
        return services[0] if len(services) == 1 else {"name": "Setup Services", "run": "echo 'Multiple services setup'"}
    
    def _get_artifact_upload_step(self, category: TestCategory) -> Dict[str, Any]:
        """Get artifact upload step."""
        return {
            "name": f"Upload {category.value} test results",
            "uses": "actions/upload-artifact@v3",
            "if": "always()",
            "with": {
                "name": f"{category.value}-test-results",
                "path": "htmlcov/\nreports/\ncomprehensive_test_results/"
            }
        }
    
    def _generate_reporting_job(self) -> Dict[str, Any]:
        """Generate comprehensive reporting job."""
        return {
            "name": "Generate Test Report",
            "runs-on": "ubuntu-latest", 
            "needs": [f"test-{cat.value}" for cat in self.config.get_enabled_categories()],
            "if": "always()",
            "steps": [
                {"uses": "actions/checkout@v4"},
                {
                    "name": "Download all artifacts",
                    "uses": "actions/download-artifact@v3"
                },
                self._get_python_setup_step(),
                self._get_poetry_setup_step(),
                self._get_dependency_install_step(),
                {
                    "name": "Generate comprehensive report",
                    "run": "poetry run python tests/test_manager.py --generate-report"
                },
                {
                    "name": "Upload final report",
                    "uses": "actions/upload-artifact@v3",
                    "with": {
                        "name": "comprehensive-test-report",
                        "path": "comprehensive_test_results/"
                    }
                }
            ]
        }
    
    def generate_jenkins_pipeline(self) -> str:
        """Generate Jenkins pipeline configuration."""
        pipeline = f"""
pipeline {{
    agent any
    
    environment {{
        POETRY_VERSION = '{self.ci_config.poetry_version}'
        PYTHON_VERSION = '{self.ci_config.python_version}'
    }}
    
    stages {{
        stage('Checkout') {{
            steps {{
                checkout scm
            }}
        }}
        
        stage('Setup') {{
            steps {{
                sh '''
                    python{self.ci_config.python_version} -m pip install poetry=={self.ci_config.poetry_version}
                    poetry install --no-interaction --no-ansi
                '''
            }}
        }}
        
        stage('Validate Infrastructure') {{
            steps {{
                sh 'poetry run python tests/test_manager.py --validate'
            }}
        }}
        
        {self._generate_jenkins_test_stages()}
        
        stage('Generate Report') {{
            steps {{
                sh 'poetry run python tests/test_manager.py --generate-report'
                
                publishHTML([
                    allowMissing: false,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'htmlcov',
                    reportFiles: 'index.html',
                    reportName: 'Coverage Report'
                ])
                
                archiveArtifacts artifacts: 'comprehensive_test_results/**/*', fingerprint: true
            }}
        }}
    }}
    
    post {{
        always {{
            cleanWs()
        }}
        failure {{
            emailext (
                subject: "Test Pipeline Failed: ${{env.JOB_NAME}} - ${{env.BUILD_NUMBER}}",
                body: "The test pipeline has failed. Please check the console output.",
                to: "${{env.CHANGE_AUTHOR_EMAIL}}"
            )
        }}
    }}
}}
"""
        return pipeline
    
    def _generate_jenkins_test_stages(self) -> str:
        """Generate Jenkins test stages."""
        stages = []
        
        for category in self.config.get_enabled_categories():
            config = self.config.get_category_config(category)
            stage = f"""
        stage('Test {config.name}') {{
            steps {{
                sh 'poetry run python tests/test_manager.py --categories {category.value}'
            }}
            post {{
                always {{
                    publishTestResults testResultsPattern: 'reports/{category.value}.xml'
                }}
            }}
        }}"""
            stages.append(stage)
        
        return ''.join(stages)
    
    def save_configurations(self):
        """Save all CI/CD configurations to files."""
        # Create directories
        github_dir = self.output_dir / ".github" / "workflows"
        github_dir.mkdir(parents=True, exist_ok=True)
        
        # Save GitHub Actions workflow
        github_workflow = self.generate_github_actions()
        github_file = github_dir / "testing-pipeline.yml"
        with open(github_file, 'w') as f:
            yaml.dump(github_workflow, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ GitHub Actions workflow saved to: {github_file}")
        
        # Save Jenkins pipeline
        jenkins_pipeline = self.generate_jenkins_pipeline()
        jenkins_file = self.output_dir / "Jenkinsfile.testing"
        with open(jenkins_file, 'w') as f:
            f.write(jenkins_pipeline)
        
        print(f"✅ Jenkins pipeline saved to: {jenkins_file}")
        
        return {
            "github_actions": str(github_file),
            "jenkins": str(jenkins_file)
        }

def main():
    """Generate CI/CD configurations."""
    print("🚀 Generating CI/CD Configurations...")
    
    config = TestConfig(environment=TestEnvironment.CI)
    generator = CIConfigGenerator(config)
    
    files = generator.save_configurations()
    
    print("\\n📊 Generated Configuration Files:")
    for ci_type, file_path in files.items():
        print(f"  {ci_type}: {file_path}")
    
    print("\\n🎉 CI/CD configuration generation complete!")

if __name__ == "__main__":
    main()
