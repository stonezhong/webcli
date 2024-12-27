const webpack = require("webpack");
const path = require("path");
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
    mode: "development",
    entry: {
        "index": './javascripts/index.js',
    },
    output: {
        path: path.resolve("static", "js-bundle"),
        filename: "[name].js",
        clean: true
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
    resolve: {
        extensions: ['.js', '.jsx'], // Allow imports without specifying extensions
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: './templates/index.html',
            filename: './webpack/templates/index.html'
        }),
    ],
}
