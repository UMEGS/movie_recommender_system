#!/bin/bash
# Start the FastAPI server

echo "🚀 Starting Movie Recommendation API..."
echo ""
echo "📚 API Documentation will be available at:"
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo ""

# Run with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

