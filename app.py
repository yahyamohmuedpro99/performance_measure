from flask import Flask, request, jsonify
from helpers import check_indentation, run_untrusted_code_with_profiling

app = Flask(__name__)


@app.route('/profile', methods=['POST'])
def profile():
    try:
        body = request.get_json()
        code = body.get('code')
        print("-----------",code)
        # Check indentation of the code
        if not check_indentation(code):
            return jsonify({"error": "Invalid indentation"}), 400
        
        # Run profiling on the code
        profiling_result = run_untrusted_code_with_profiling(code)

        # Return the profiling result as JSON response
        return jsonify({"result": profiling_result}), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == '__main__':
    app.run(debug=True)
