"""
Data Tools Module
--------------
This module provides data-related tools for the agent.
"""

import os
import json
import csv
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

import numpy as np
import pandas as pd
from utils.logger import get_logger


class DataTools:
    """Provides data-related tools for the agent."""
    
    def __init__(self):
        """Initialize the data tools."""
        self.logger = get_logger(__name__)
    
    async def load_csv(self, path: str) -> Dict[str, Any]:
        """
        Load a CSV file and parse it.
        
        Args:
            path: The path to the CSV file
            
        Returns:
            A dictionary with the parsed data
        """
        try:
            file_path = Path(path)
            
            # Check if the file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Read the CSV file
            df = pd.read_csv(file_path)
            
            # Get basic information about the data
            rows, cols = df.shape
            columns = df.columns.tolist()
            dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
            
            # Get a sample of the data
            sample = df.head(5).to_dict(orient="records")
            
            # Get summary statistics
            try:
                stats = df.describe().to_dict()
            except:
                stats = {}
            
            return {
                "success": True,
                "rows": rows,
                "columns": cols,
                "column_names": columns,
                "dtypes": dtypes,
                "sample": sample,
                "stats": stats
            }
        
        except Exception as e:
            self.logger.error(f"Error loading CSV file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def load_json(self, path: str) -> Dict[str, Any]:
        """
        Load a JSON file and parse it.
        
        Args:
            path: The path to the JSON file
            
        Returns:
            A dictionary with the parsed data
        """
        try:
            file_path = Path(path)
            
            # Check if the file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Read the JSON file
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Get basic information about the data
            data_type = type(data).__name__
            
            if isinstance(data, dict):
                keys = list(data.keys())
                num_items = len(keys)
                sample = {k: data[k] for k in keys[:5]} if keys else {}
            elif isinstance(data, list):
                num_items = len(data)
                sample = data[:5] if data else []
                if sample and isinstance(sample[0], dict):
                    keys = list(sample[0].keys())
                else:
                    keys = []
            else:
                num_items = 1
                sample = data
                keys = []
            
            return {
                "success": True,
                "data_type": data_type,
                "num_items": num_items,
                "keys": keys,
                "sample": sample
            }
        
        except Exception as e:
            self.logger.error(f"Error loading JSON file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_csv(self, data: List[Dict[str, Any]], path: str) -> Dict[str, Any]:
        """
        Save data to a CSV file.
        
        Args:
            data: The data to save
            path: The path to save the data to
            
        Returns:
            A dictionary with the result
        """
        try:
            file_path = Path(path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Save to CSV
            df.to_csv(file_path, index=False)
            
            return {
                "success": True,
                "path": str(file_path),
                "rows": len(data),
                "columns": len(df.columns) if not df.empty else 0
            }
        
        except Exception as e:
            self.logger.error(f"Error saving data to CSV file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_json(self, data: Any, path: str) -> Dict[str, Any]:
        """
        Save data to a JSON file.
        
        Args:
            data: The data to save
            path: The path to save the data to
            
        Returns:
            A dictionary with the result
        """
        try:
            file_path = Path(path)
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            
            return {
                "success": True,
                "path": str(file_path),
                "data_type": type(data).__name__
            }
        
        except Exception as e:
            self.logger.error(f"Error saving data to JSON file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def analyze_data(self, path: str) -> Dict[str, Any]:
        """
        Analyze data and provide insights.
        
        Args:
            path: The path to the data file
            
        Returns:
            A dictionary with the analysis result
        """
        try:
            file_path = Path(path)
            
            # Check if the file exists
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}"
                }
            
            # Determine file type and load the data
            if file_path.suffix.lower() == ".csv":
                df = pd.read_csv(file_path)
            elif file_path.suffix.lower() == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    df = pd.DataFrame(data)
                else:
                    return {
                        "success": False,
                        "error": "JSON file is not in a format that can be analyzed (not a list of objects)"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_path.suffix}"
                }
            
            # Basic statistics
            basic_stats = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing_values": df.isnull().sum().to_dict()
            }
            
            # Descriptive statistics for numeric columns
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                numeric_stats = df[numeric_cols].describe().to_dict()
            else:
                numeric_stats = {}
            
            # Categorical statistics
            categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            categorical_stats = {}
            
            for col in categorical_cols:
                try:
                    value_counts = df[col].value_counts().to_dict()
                    unique_values = len(value_counts)
                    top_values = dict(sorted(value_counts.items(), key=lambda x: x[1], reverse=True)[:5])
                    categorical_stats[col] = {
                        "unique_values": unique_values,
                        "top_values": top_values
                    }
                except:
                    pass
            
            # Correlations between numeric columns
            correlations = {}
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr().round(2)
                
                # Get top correlations
                corr_pairs = []
                for i in range(len(numeric_cols)):
                    for j in range(i+1, len(numeric_cols)):
                        col1 = numeric_cols[i]
                        col2 = numeric_cols[j]
                        corr = corr_matrix.iloc[i, j]
                        if not pd.isna(corr):
                            corr_pairs.append({
                                "column1": col1,
                                "column2": col2,
                                "correlation": corr
                            })
                
                # Sort by absolute correlation
                corr_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)
                correlations = {
                    "matrix": corr_matrix.to_dict(),
                    "top_pairs": corr_pairs[:5]
                }
            
            return {
                "success": True,
                "basic_stats": basic_stats,
                "numeric_stats": numeric_stats,
                "categorical_stats": categorical_stats,
                "correlations": correlations
            }
        
        except Exception as e:
            self.logger.error(f"Error analyzing data file {path}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def plot_data(self, data: Union[List[Dict[str, Any]], str], plot_type: str, 
                        x_column: Optional[str] = None, y_column: Optional[str] = None,
                        title: Optional[str] = None, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a plot of data.
        
        Args:
            data: The data to plot (either a list of dictionaries or a path to a CSV/JSON file)
            plot_type: The type of plot to create (bar, line, scatter, etc.)
            x_column: The column to use for the x-axis
            y_column: The column to use for the y-axis
            title: The title of the plot
            output_path: The path to save the plot image
            
        Returns:
            A dictionary with the result
        """
        try:
            # Load the data
            if isinstance(data, str):
                file_path = Path(data)
                
                # Check if the file exists
                if not file_path.exists():
                    return {
                        "success": False,
                        "error": f"File not found: {data}"
                    }
                
                # Determine file type and load the data
                if file_path.suffix.lower() == ".csv":
                    df = pd.read_csv(file_path)
                elif file_path.suffix.lower() == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if isinstance(data, list) and data and isinstance(data[0], dict):
                        df = pd.DataFrame(data)
                    else:
                        return {
                            "success": False,
                            "error": "JSON file is not in a format that can be plotted (not a list of objects)"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported file type: {file_path.suffix}"
                    }
            else:
                df = pd.DataFrame(data)
            
            # Verify columns existence
            if x_column and x_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column not found: {x_column}"
                }
            
            if y_column and y_column not in df.columns:
                return {
                    "success": False,
                    "error": f"Column not found: {y_column}"
                }
            
            # Set default title
            if not title:
                if x_column and y_column:
                    title = f"{y_column} vs {x_column}"
                elif x_column:
                    title = f"{x_column}"
                elif y_column:
                    title = f"{y_column}"
                else:
                    title = "Data Plot"
            
            # Set default output path
            if not output_path:
                output_dir = Path("data/plots")
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = str(output_dir / f"plot_{plot_type}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png")
            else:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create the plot
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            
            if plot_type == "bar":
                if x_column and y_column:
                    df.plot(kind="bar", x=x_column, y=y_column)
                elif x_column:
                    df[x_column].value_counts().plot(kind="bar")
                else:
                    return {
                        "success": False,
                        "error": "Bar plot requires at least x_column"
                    }
            
            elif plot_type == "line":
                if x_column and y_column:
                    df.plot(kind="line", x=x_column, y=y_column)
                else:
                    return {
                        "success": False,
                        "error": "Line plot requires both x_column and y_column"
                    }
            
            elif plot_type == "scatter":
                if x_column and y_column:
                    df.plot(kind="scatter", x=x_column, y=y_column)
                else:
                    return {
                        "success": False,
                        "error": "Scatter plot requires both x_column and y_column"
                    }
            
            elif plot_type == "hist":
                if x_column:
                    df[x_column].plot(kind="hist")
                else:
                    return {
                        "success": False,
                        "error": "Histogram requires x_column"
                    }
            
            elif plot_type == "pie":
                if x_column:
                    df[x_column].value_counts().plot(kind="pie")
                else:
                    return {
                        "success": False,
                        "error": "Pie chart requires x_column"
                    }
            
            else:
                return {
                    "success": False,
                    "error": f"Unsupported plot type: {plot_type}"
                }
            
            # Set title and labels
            plt.title(title)
            
            if x_column:
                plt.xlabel(x_column)
            
            if y_column:
                plt.ylabel(y_column)
            
            # Save the plot
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()
            
            return {
                "success": True,
                "plot_type": plot_type,
                "output_path": output_path,
                "title": title
            }
        
        except Exception as e:
            self.logger.error(f"Error creating plot: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


def get_data_tools() -> Dict[str, Any]:
    """
    Get the data tools.
    
    Returns:
        A dictionary of data tool functions
    """
    tools = DataTools()
    
    return {
        "load_csv": tools.load_csv,
        "load_json": tools.load_json,
        "save_csv": tools.save_csv,
        "save_json": tools.save_json,
        "analyze_data": tools.analyze_data,
        "plot_data": tools.plot_data
    }