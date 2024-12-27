const webpack = require("webpack");
const path = require("path");
const HtmlWebpackPlugin = require('html-webpack-plugin');

module.exports = {
    mode: "development",
    entry: {
        "index": './javascripts/index.js',
        "admin": './javascripts/admin.js',
    },
    output: {
        path: path.resolve("dist"),
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
            filename: 'templates/index.html',
            publicPath: '/dist/',
            chunks: ['index']
        }),
    ],
}
