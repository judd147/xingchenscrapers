"""
Simple ML Model Test Script
Quick test of the ML model with your historical data

Usage: python test_ml_model.py
"""

import os
import pandas as pd
from dotenv import load_dotenv
import warnings
from datetime import datetime

# Import the ML model
from ML_model import SoccerMLPredictor

warnings.filterwarnings("ignore")


def main():
    print("=" * 60)
    print("ML模型快速测试")
    print("=" * 60)

    try:
        # Load environment variables
        load_dotenv()

        # Get data path
        data_path = os.getenv("LOCAL_DATA_PATH")
        if not data_path:
            print("错误: LOCAL_DATA_PATH 环境变量未设置")
            return

        print(f"数据路径: {data_path}")

        # Load data
        print("\n1. 加载数据...")
        df = pd.read_excel(
            data_path,
            sheet_name=1,
            converters={
                "年": str,
                "盘口": str,
                "竞彩": str,
                "比分": str,
                "主赔": float,
                "客赔": float,
            },
        )

        # Clean data
        df["盘口数字"] = df["盘口"].astype(float)
        df["算法"] = df["算法"].fillna("球伯乐")
        df["注释"] = df["注释"].fillna("")

        print(f"数据加载完成: {len(df)} 行")

        # Filter training data
        training_data = df[(df["H"].notna()) & (df["A"].notna())].copy()
        print(f"可用于训练的数据: {len(training_data)} 行")

        if len(training_data) < 50:
            print("警告: 训练数据不足")
            return

        # Initialize ML system
        print("\n2. 初始化ML模型...")
        ml_system = SoccerMLPredictor()

        # Train models
        print("\n3. 训练模型...")
        results, features, targets = ml_system.train_models(training_data)

        # Show results
        print("\n4. 模型性能:")
        for model_name, result in results.items():
            print(f"  {model_name}:")
            print(f"    训练准确率: {result['train_accuracy']:.3f}")
            print(f"    测试准确率: {result['test_accuracy']:.3f}")
            print(f"    交叉验证: {result['cv_mean']:.3f} ± {result['cv_std']:.3f}")

        # Find best model
        best_model = max(results.keys(), key=lambda x: results[x]["test_accuracy"])
        print(
            f"\n最佳模型: {best_model} (准确率: {results[best_model]['test_accuracy']:.3f})"
        )

        # Run backtest
        print("\n5. 运行回测...")
        backtest_df, accuracy = ml_system.backtest_predictions(training_data)

        if backtest_df is not None and len(backtest_df) > 0:
            print(f"回测准确率: {accuracy:.3f} ({accuracy*100:.1f}%)")
            print(f"回测场次: {len(backtest_df)}")

            # Show high confidence results
            if "confidence" in backtest_df.columns:
                high_conf = backtest_df[backtest_df["confidence"] >= 0.7]
                if len(high_conf) > 0:
                    high_conf_accuracy = high_conf["correct"].mean()
                    print(
                        f"高置信度准确率: {high_conf_accuracy:.3f} ({len(high_conf)} 场)"
                    )

        # Save model and test load + single prediction
        print("\n6. 保存并加载模型...")
        model_path = os.getenv("ML_MODEL_PATH", "saved_model.pkl")
        try:
            ml_system.save_model(model_path)
            print(f"模型已保存: {model_path}")
            ml_loaded = SoccerMLPredictor.load_model(model_path)
        except Exception as e:
            print(f"保存/加载模型失败: {e}")
            ml_loaded = ml_system

        # Test single prediction
        print("\n7. 测试单场预测...")
        if len(training_data) > 0:
            sample_match = training_data.iloc[0]
            try:
                prediction = ml_loaded.predict_single_match(sample_match)
                print(f"样本比赛: {sample_match.get('比赛', 'Unknown')}")
                print(f"预测结果: {prediction['prediction']}")
                print(f"置信度: {prediction.get('confidence', 0):.3f}")
                print(f"强度: {prediction.get('strength', 'Unknown')}")
            except Exception as e:
                print(f"单场预测失败: {e}")

        # Save results
        print("\n8. 保存回测结果...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if backtest_df is not None and len(backtest_df) > 0:
            filename = f"quick_test_results_{timestamp}.xlsx"
            backtest_df.to_excel(filename, index=False)
            print(f"结果已保存: {filename}")

        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)

    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
