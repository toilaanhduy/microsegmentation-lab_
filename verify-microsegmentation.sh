#!/usr/bin/env bash
NAMESPACE="micro-app"

echo "=================================================="
echo " BẮT ĐẦU KIỂM THỬ NÂNG CAO K8S NETWORK POLICY"
echo "=================================================="

# Test 1: Frontend -> Backend (Phải thành công)
echo -n "[Test 1] Frontend -> Backend (TCP 8000): "
kubectl run test-fe-be -n $NAMESPACE --rm -i --restart='Never' --image=curlimages/curl --labels="app=frontend" -- \
  curl -s --connect-timeout 3 http://backend:8000/items > /dev/null && echo "PASS (Được phép)" || echo "FAIL"

# Test 2: Frontend -> Database (Phải bị chặn hoàn toàn theo Zero-Trust)
echo -n "[Test 2] Frontend -> Database (TCP 5432): "
kubectl run test-fe-db -n $NAMESPACE --rm -i --restart='Never' --image=busybox --labels="app=frontend" -- \
  nc -z -w 3 database 5432 > /dev/null 2>&1 && echo "FAIL (Không bị chặn)" || echo "PASS (Đã bị chặn)"

# Test 3: Backend -> Database (Phải thành công)
echo -n "[Test 3] Backend -> Database (TCP 5432): "
kubectl run test-be-db -n $NAMESPACE --rm -i --restart='Never' --image=busybox --labels="app=backend" -- \
  nc -z -w 3 database 5432 > /dev/null 2>&1 && echo "PASS (Được phép)" || echo "FAIL"

# Test 4: Unauthorized Pod -> Backend (Giả lập kẻ tấn công ngoài luồng - Phải bị chặn)
echo -n "[Test 4] Unauthorized Pod -> Backend (TCP 8000): "
kubectl run test-rogue-be -n $NAMESPACE --rm -i --restart='Never' --image=busybox --labels="app=rogue" -- \
  nc -z -w 3 backend 8000 > /dev/null 2>&1 && echo "FAIL (Không bị chặn)" || echo "PASS (Đã bị chặn tuyệt đối)"

echo "=================================================="
echo " HOÀN TẤT TẤT CẢ CÁC BÀI KIỂM THỬ NÂNG CAO!"
echo "=================================================="