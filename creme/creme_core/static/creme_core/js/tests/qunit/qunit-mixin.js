
(function($) {
    "use strict";

    window.QUnitMixin = function() {
        var self = this;
        var reserved = ['setup', 'teardown', 'beforeEach', 'afterEach'];
        var mixins = this.__mixins = [QUnitBaseMixin].concat(Array.copy(arguments));

        mixins.forEach(function(mixin) {
            for (var key in mixin) {
                if (reserved.indexOf(key) === -1) {
                    self[key] = mixin[key];
                }
            }
        });
    };

    window.QUnit.skipIf = function(condition, name, callable) {
        var skipIt = Object.isFunc(condition) ? condition() : Boolean(condition);

        if (skipIt) {
            QUnit.skip(name, callable);
        } else {
            QUnit.test(name, callable);
        }
    };

    window.QUnit.browsers = {
        isChrome: function() {
            // headless chrome does not have window.chrome defined
            // (see https://github.com/ChromeDevTools/devtools-protocol/issues/83)
            return !!window.chrome || /HeadlessChrome/.test(window.navigator.userAgent);
        },
        isHeadless: function() {
            return Object.isNone(navigator.webdriver) === false;
        },
        isFirefox: function() {
            return 'MozAppearance' in document.documentElement.style;
        }
    };

    window.QUnit.parameterize = function(name, scenarios, callable) {
        (scenarios || []).forEach(function(scenario, index) {
            QUnit.test('${name}-${index}'.template({name: name, index: index + 1}), function(assert) {
                callable.apply(this, (Array.isArray(scenario) ? scenario : [scenario]).concat([assert]));
            });
        });
    };

    /* An alias for me */
    window.QUnit.parametrize = window.QUnit.parameterize;

    QUnitMixin.prototype = {
        beforeEach: function(env) {
            var self = this;

            this.__mixins.forEach(function(mixin) {
                if (Object.isFunc(mixin.beforeEach)) {
                    mixin.beforeEach.call(self, env);
                }
            });
        },

        afterEach: function(env) {
            var self = this;

            Array.copy(this.__mixins).reverse().forEach(function(mixin) {
                if (Object.isFunc(mixin.afterEach)) {
                    mixin.afterEach.call(self, env);
                }
            });
        }
    };

    var listChildrenTags = function() {
        return $('body').children().map(function() {
            var attributes = [];

            for (var i = 0; i < this.attributes.length; ++i) {
                attributes.push('${name}="${value}"'.template({
                    name: this.attributes[i].name,
                    value: this.attributes[i].value.replace('"', '\\"')
                }));
            }

            return '<${tagName} ${attrs}>'.template({
                tagName: this.tagName.toLowerCase(),
                attrs: attributes.join(' ')
            });
        }).get();
    };

    window.QUnitBaseMixin = {
        beforeEach: function(env) {
            // console.log(env.test.testName);
            this.__qunitDOMCleanupCheckError = 'ignore';
            this.__qunitBodyElementTags = listChildrenTags($('body'));
            this.qunitFixture().attr('style', 'position: absolute;top: -10000px;left: -10000px;width: 1000px;height: 1000px;');
        },

        afterEach: function(env) {
            var tags =  listChildrenTags($('body'));
            var checkStatus = this.qunitDOMCleanupCheck();

            if (checkStatus === 'ignore') {
                return;
            }

            if (this.__qunitBodyElementTags.length !== tags.length) {
                var message = 'QUnit incomplete DOM cleanup (expected ${expected}, got ${count})'.template({
                    expected: this.__qunitBodyElementTags.length,
                    count: tags.length
                });

                if (this.qunitDOMCleanupCheck() === 'error') {
                    deepEqual(tags.sort(), this.__qunitBodyElementTags.sort(), message);
                } else {
                    console.warn(message);
                }
            }
        },

        qunitDOMCleanupCheck: function(status) {
            if (status === undefined) {
                return this.__qunitSkipDOMCleanupCheck;
            }

            this.__qunitSkipDOMCleanupCheck = status;
            return this;
        },

        qunitFixture: function(name) {
            var fixture = $('#qunit-fixture');

            if (fixture.size() === 0) {
                throw Error('Missing qunit-fixture element !');
            };

            if (name === undefined || name === null) {
                return fixture;
            }

            name = String(name);
            var subfixture = fixture.find('#qunit-fixture-' + name);

            if (subfixture.length === 0) {
                subfixture = $('<div id="qunit-fixture-' + name + '"></div>').appendTo(fixture);
            }

            return subfixture;
        },

        assertRaises: function(block, expected, message) {
            expected = expected || Error;

            QUnit.assert.raises(
                block,
                function(error) {
                    ok(error instanceof expected, 'error is ' + expected);

                    if (message !== undefined) {
                        equal(message, '' + error, 'expected message');
                    }

                    block.__raised = error;
                    return true;
                }
            );

            return block.__raised;
        },

        equalHtml: function(expected, element, message) {
            QUnit.assert.equal($('<div>').append(expected).html(), $(element).html(), message);
        },

        equalOuterHtml: function(expected, element, message) {
            QUnit.assert.equal($('<div>').append(expected).html(), $('<div>').append($(element).clone()).html(), message);
        },

        fakeMethod: function(instance, method, follow) {
            var faker = new FunctionFaker({
                instance: instance,
                method: method,
                follow: follow
            });

            faker.wrap();
            return faker;
        },

        withFakeMethod: function(instance, property, follow, block) {
            return new FunctionFaker({
                instance: instance,
                method: method,
                follow: follow
            }).with(block.bind(this));
        }
    };

    window.QUnitConsoleMixin = {
        beforeEach: function() {
            this.resetMockConsoleWarnCalls();

            var self = this;
            var __consoleWarn = this.__consoleWarn = console.warn;
            var __consoleError = this.__consoleError = console.error;

            console.warn = function() {
                var args = Array.copy(arguments);
                self.__consoleWarnCalls.push(args);
                return __consoleWarn.apply(this, args);
            };

            console.error = function() {
                var args = Array.copy(arguments);
                self.__consoleErrorCalls.push(args);
                return __consoleError.apply(this, args);
            };
        },

        afterEach: function() {
            console.warn = this.__consoleWarn;
            console.error = this.__consoleError;
        },

        mockConsoleWarnCalls: function() {
            return this.__consoleWarnCalls;
        },

        resetMockConsoleWarnCalls: function() {
            this.__consoleWarnCalls = [];
        },

        mockConsoleErrorCalls: function() {
            return this.__consoleWarnCalls;
        },

        resetMockConsoleErrorCalls: function() {
            this.__consoleWarnCalls = [];
        }
    };

    window.QUnitMouseMixin = {
        fakeMouseEvent: function(name, options) {
            options = options || {};
            var position = options.position || {};
            var offset = options.offset || {};

            return $.Event(name, {
                which: options.which || 1,     // Mouse button 1 (left), 2 (middle), 3 (right)
                pageX: position.left || 0,     // The mouse position relative to the left edge of the document.
                pageY: position.top || 0,      // The mouse position relative to the top edge of the document.
                offsetX: offset.left || 0,
                offsetY: offset.top || 0,
                button: options.which || 1,
                originalEvent: {}
            });
        },

        fakeDragNDrop: function(source, target, options) {
            options = options || {};

            var dragPosition = source.offset();
            var dragOffset = {
                left: source.width() / 2,
                top: source.height() / 2
            };

            var dropPosition = {
                left: target.offset().left + 10,
                top: target.offset().top + 10
            };

            // LEFT mouse button down !
            source.trigger(
                this.fakeMouseEvent('mousedown', {
                    position: dragPosition,
                    offset: dragOffset
                }, options.mouseDown)
            );

            source.trigger(
                this.fakeMouseEvent('mousemove', {
                    position: dropPosition
                }, options.mouseMove)
            );

            target.trigger(
                this.fakeMouseEvent('mouseup', {
                    position: dropPosition
                }, options.mouseUp)
            );
        }
    };
}(jQuery));
