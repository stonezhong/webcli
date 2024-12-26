const webpack = require("webpack");
const path = require("path");

module.exports = {
    mode: "development",
    externals: {
        react: 'React',
        'react-dom': 'ReactDOM',
    },
    entry: {
    },
    output: {
        path: path.resolve("explorer", "static", "js-bundle"),
        filename: "[name].js"
    },
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: [
                    {
                        loader: "babel-loader",
                    }
                ],
            },
        ]
    },
    devtool: '#inline-source-map'
}
