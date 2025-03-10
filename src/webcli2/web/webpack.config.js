const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

module.exports = (env, argv) => {
    const isProduction = argv.mode === 'production';
    return {
         stats: 'detailed',

        /****************************************
         * You can generate multiple javascript bundle, each bundle has a unique name
         */
        entry: {
            "thread_page"   : "./javascripts/thread_page.js",
            "login_page"  : "./javascripts/login_page.js",
            "threads_page": "./javascripts/threads_page.js",
            "test_page" : "./javascripts/test_page.js"
        },

        output: {
            filename: isProduction ? '[name].[contenthash].js' : '[name].js',
            path: path.resolve(__dirname, 'dist'), // Output directory
            assetModuleFilename: 'assets/[hash][ext][query]',
        },

        mode: isProduction ? 'production' : 'development',

        /****************************************
         * If you want to use javascript library and do not want them being part of javascript bundle, put them here
         * Remember, you need to include them in you HTML file explicitly using script tag
         */
        externals: {
            jquery: 'jQuery', // Use the global jQuery variable
            jquery: '$',      // jquery can be either referenced with '$' or 'jQuery'
        },

        devtool: isProduction ? 'source-map' : 'eval-source-map',

        module: {
            rules: [
                /****************************************
                 * Since we are using ES6 with react, we need this
                 */
                {
                    test: /\.(js|jsx)$/,
                    exclude: /node_modules/,
                    use: [
                        {
                            loader: "babel-loader",
                        }
                    ],
                },

                /****************************************
                 * This allows us to import css, sass files in javascript
                 */
                {
                    test: /\.s?css$/,
                    use: [
                        isProduction ? MiniCssExtractPlugin.loader : 'style-loader',
                        'css-loader',
                        'sass-loader',
                    ],                
                },
            ]
        },

        /****************************************
         * Allow imports without specifying extensions
         */
        resolve: {
            alias: {
                "@": path.resolve(__dirname, 'javascripts')
            },
            extensions: ['.js', '.jsx'],
        },

        plugins: [
            new CleanWebpackPlugin(), // Cleans the output folder before building,

            /****************************************
             * Specify each HTML file you want to inject javascript bundle here
             */
            new HtmlWebpackPlugin({
                template: './templates/thread_page.html',       // source of the HTML file is here
                filename: 'templates/thread_page.html',         // specify where is the generated HTML file under dist directory
                publicPath: '/dist/',                           // When loading the javascript from this HTML template, where is the js bundle? It will insert like this to the generate HTML template
                                                                //  <script defer src="/dist/index.js"></script>
                chunks: ['thread_page']                         // only include javascript bundle for thread_page, see entry section
            }),
            new HtmlWebpackPlugin({
                template: './templates/login_page.html',
                filename: 'templates/login_page.html',
                publicPath: '/dist/',
                chunks: ['login_page']
            }),
            new HtmlWebpackPlugin({
                template: './templates/threads_page.html',
                filename: 'templates/threads_page.html',
                publicPath: '/dist/',
                chunks: ['threads_page']
            }),
            new HtmlWebpackPlugin({
                template: './templates/test_page.html',
                filename: 'templates/test_page.html',
                publicPath: '/dist/',
                chunks: ['test_page']
            }),
        ],
    };
};
