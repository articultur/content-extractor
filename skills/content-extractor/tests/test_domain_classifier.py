"""Tests for DomainClassifier."""

from models.structured import Function


def test_function_domain_field():
    func = Function(
        id="func_001", name="登录", name_normalized="login", domain=None
    )
    assert hasattr(func, 'domain')
    assert func.domain is None


def test_classify_function_domain():
    from associator.domain_classifier import DomainClassifier
    classifier = DomainClassifier()
    func = Function(
        id="func_001", name="用户登录", name_normalized="user_login",
        trigger="点击登录按钮", action="验证密码"
    )
    domain = classifier.classify(func)
    assert domain is not None
    assert isinstance(domain, str)
    assert domain in ["认证模块", "账户模块", "首页模块", "订单模块", "支付模块", "通知模块", "报表模块", "搜索模块", "安全模块", "配置模块", "通用"]


def test_domain_classifier_auth():
    from associator.domain_classifier import DomainClassifier
    classifier = DomainClassifier()
    func = Function(id="f1", name="登录验证", name_normalized="login_verify",
                    trigger="输入密码", action="系统验证密码")
    assert classifier.classify(func) == "认证模块"


def test_domain_classifier_payment():
    from associator.domain_classifier import DomainClassifier
    classifier = DomainClassifier()
    func = Function(id="f2", name="支付订单", name_normalized="pay_order",
                    trigger="点击支付", action="扣款")
    assert classifier.classify(func) == "支付模块"